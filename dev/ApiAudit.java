package syx.dev;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;
import java.net.URI;
import javax.tools.*;
import javax.lang.model.element.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;
import syx.assistant.JsonWriter;

/** Development-time compiler inspection. No reflection or inspection inside the running game. */
public final class ApiAudit {
    static final Map<String,Map<String,Object>> members=new TreeMap<>();
    static String hash(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }
    static boolean gameType(String n) {
        return n.startsWith("game.")||n.startsWith("settlement.")||n.startsWith("world.")||n.startsWith("init.")||
            n.startsWith("snake2d.")||n.startsWith("script.")||n.startsWith("view.")||n.startsWith("util.");
    }
    static String sourcePath(TypeElement owner) {
        while(owner.getEnclosingElement() instanceof TypeElement)owner=(TypeElement)owner.getEnclosingElement();
        return owner.getQualifiedName().toString().replace('.','/')+".java";
    }
    static void record(Element element,CompilationUnitTree unit,Tree node,Trees trees) {
        if(element==null || !(element.getEnclosingElement() instanceof TypeElement))return;
        TypeElement owner=(TypeElement)element.getEnclosingElement();
        String type=owner.getQualifiedName().toString();if(!gameType(type))return;
        if(!Set.of(ElementKind.METHOD,ElementKind.CONSTRUCTOR,ElementKind.FIELD,ElementKind.ENUM_CONSTANT).contains(element.getKind()))return;
        String signature=type+"#"+element.toString();
        Map<String,Object> entry=members.computeIfAbsent(signature,k->{
            Map<String,Object> e=new LinkedHashMap<>();e.put("id",signature);e.put("owner",type);
            e.put("name",element.getSimpleName().toString());e.put("kind",element.getKind().name());
            e.put("signature",element.toString());e.put("public",element.getModifiers().contains(Modifier.PUBLIC));
            e.put("source_file",sourcePath(owner));e.put("uses",new TreeSet<String>());
            e.put("parameter_types",element instanceof ExecutableElement?((ExecutableElement)element).getParameters().stream().map(v->v.asType().toString()).toList():List.of());
            e.put("compiler_generated_enum",owner.getKind()==ElementKind.ENUM && element.getSimpleName().contentEquals("values"));
            e.put("arity",element instanceof ExecutableElement?((ExecutableElement)element).getParameters().size():-1);
            return e;
        });
        long pos=trees.getSourcePositions().getStartPosition(unit,node);
        @SuppressWarnings("unchecked") Set<String> uses=(Set<String>)entry.get("uses");
        uses.add(Paths.get(unit.getSourceFile().toUri()).getFileName()+":"+unit.getLineMap().getLineNumber(pos));
    }
    static final class Source extends SimpleJavaFileObject {
        final String text;
        Source(String name,String text){super(URI.create("string:///"+name),Kind.SOURCE);this.text=text;}
        @Override public CharSequence getCharContent(boolean ignored){return text;}
    }
    static String simpleTypes(Object types) {
        return types.toString().replaceAll("(?:[a-z][a-zA-Z0-9_$]*\\.)+", "").replace(" ", "");
    }
    public static void main(String[] args) throws Exception {
        Path jar=Paths.get(args[0]),src=Paths.get(args[1]),sources=Paths.get(args[2]),output=Paths.get(args[3]);
        JavaCompiler compiler=ToolProvider.getSystemJavaCompiler();
        DiagnosticCollector<JavaFileObject> diagnostics=new DiagnosticCollector<>();
        try(StandardJavaFileManager fm=compiler.getStandardFileManager(diagnostics,null,StandardCharsets.UTF_8)) {
            List<Path> files;
            try(var paths=Files.walk(src)){files=paths.filter(p->p.toString().endsWith(".java")).sorted().toList();}
            JavacTask task=(JavacTask)compiler.getTask(null,fm,diagnostics,List.of("--release","16","-proc:none","-classpath",jar.toString()),null,fm.getJavaFileObjectsFromPaths(files));
            Iterable<? extends CompilationUnitTree> units=task.parse();task.analyze();Trees trees=Trees.instance(task);
            for(CompilationUnitTree unit:units)new TreePathScanner<Void,Void>() {
                @Override public Void visitMethodInvocation(MethodInvocationTree n,Void v){record(trees.getElement(getCurrentPath()),unit,n,trees);return super.visitMethodInvocation(n,v);}
                @Override public Void visitNewClass(NewClassTree n,Void v){record(trees.getElement(getCurrentPath()),unit,n,trees);return super.visitNewClass(n,v);}
                @Override public Void visitMemberSelect(MemberSelectTree n,Void v){record(trees.getElement(getCurrentPath()),unit,n,trees);return super.visitMemberSelect(n,v);}
                @Override public Void visitIdentifier(IdentifierTree n,Void v){record(trees.getElement(getCurrentPath()),unit,n,trees);return super.visitIdentifier(n,v);}
            }.scan(unit,null);
            if(diagnostics.getDiagnostics().stream().anyMatch(d->d.getKind()==Diagnostic.Kind.ERROR))throw new IllegalStateException(diagnostics.getDiagnostics().toString());
        }
        try(ZipFile zip=new ZipFile(sources.toFile())) {
            Map<String,List<Map<String,Object>>> declarations=new HashMap<>();
            Set<String> needed=new TreeSet<>();for(var member:members.values())needed.add((String)member.get("source_file"));
            for(String name:needed) {
                ZipEntry entry=zip.getEntry(name);if(entry==null)continue;
                byte[] raw=zip.getInputStream(entry).readAllBytes();String digest=hash(raw);
                JavacTask parser=(JavacTask)compiler.getTask(null,null,null,List.of("-proc:none"),null,List.of(new Source(name,new String(raw,StandardCharsets.UTF_8))));
                DocTrees docs=DocTrees.instance(parser);
                for(CompilationUnitTree unit:parser.parse())new TreePathScanner<Void,String>() {
                    @Override public Void visitClass(ClassTree n,String prefix){
                        if(n.getSimpleName().length()==0)return null;
                        String owner=(prefix==null?unit.getPackageName().toString():prefix)+"."+n.getSimpleName();
                        return super.visitClass(n,owner);
                    }
                    void add(Tree node,String owner,String member,int arity) {
                        long at=docs.getSourcePositions().getStartPosition(unit,node);
                        var data=new LinkedHashMap<String,Object>();data.put("line",unit.getLineMap().getLineNumber(at));
                        data.put("source_sha256",digest);
                        data.put("parameter_types",node instanceof MethodTree?((MethodTree)node).getParameters().stream().map(v->v.getType().toString()).toList():List.of());
                        data.put("has_javadoc",docs.getDocCommentTree(getCurrentPath())!=null);
                        declarations.computeIfAbsent(owner+"#"+member+"/"+arity,k->new ArrayList<>()).add(data);
                    }
                    @Override public Void visitMethod(MethodTree n,String owner){add(n,owner,n.getName().toString(),n.getParameters().size());return null;}
                    @Override public Void visitVariable(VariableTree n,String owner){add(n,owner,n.getName().toString(),-1);return null;}
                }.scan(unit,null);
            }
            for(var member:members.values()) {
                String key=member.get("owner")+"#"+member.get("name")+"/"+member.get("arity");
                List<Map<String,Object>> matched=declarations.getOrDefault(key,List.of());
                if(matched.size()>1) {
                    Object expected=member.get("parameter_types");
                    matched=matched.stream().filter(c->simpleTypes(c.get("parameter_types")).equals(simpleTypes(expected))).toList();
                }
                member.put("source_candidates",matched);
                member.put("source_match",matched.isEmpty()?(Boolean.TRUE.equals(member.get("compiler_generated_enum"))?"compiler_generated_enum_member":"not_found"):matched.size()==1?"name_arity_and_simple_parameter_types":"ambiguous_overload");
                member.put("documentation_status","human_review_required; Javadoc presence alone does not establish a stable mod contract");
            }
        }
        Map<String,Object> report=new LinkedHashMap<>();report.put("schema_version",1);
        report.put("game_jar_sha256",hash(Files.readAllBytes(jar)));report.put("source_archive_sha256",hash(Files.readAllBytes(sources)));
        report.put("method","Java compiler attribution of production mod references; source anchors match declaring type/name/arity, not method body equivalence");
        Map<String,Object> modHashes=new LinkedHashMap<>();
        try(var paths=Files.walk(src)) {
            for(Path path:paths.filter(p->p.toString().endsWith(".java")).sorted().toList())
                modHashes.put(src.relativize(path).toString().replace('\\','/'),hash(Files.readAllBytes(path)));
        }
        report.put("mod_source_sha256",modHashes);
        report.put("members",new ArrayList<>(members.values()));
        Files.createDirectories(output.toAbsolutePath().getParent());Files.writeString(output,JsonWriter.encode(report)+"\n");
        System.out.println("Audited "+members.size()+" game API members; non-public references: "+members.values().stream().filter(m->!Boolean.TRUE.equals(m.get("public"))).count());
    }
}
