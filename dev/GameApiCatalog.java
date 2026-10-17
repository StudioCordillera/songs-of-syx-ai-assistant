package syx.dev;

import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.net.URI;
import java.util.*;
import java.util.zip.*;
import javax.tools.*;
import javax.lang.model.element.*;
import com.sun.source.tree.*;
import com.sun.source.util.*;
import syx.assistant.JsonWriter;

/** Offline metadata inspection of licensed references. Never runs or reflects on game classes. */
public final class GameApiCatalog {
    static String hash(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }
    static final class Source extends SimpleJavaFileObject {
        final String text;
        Source(String name,String text) {super(URI.create("string:///"+name),Kind.SOURCE);this.text=text;}
        @Override public CharSequence getCharContent(boolean ignored) {return text;}
    }
    static String simple(String value) {
        return value.replaceAll("(?:[a-z][a-zA-Z0-9_$]*\\.)+", "").replace(" ", "").replace("...", "[]");
    }
    static boolean accessible(TypeElement type) {
        Element e=type;
        while(e instanceof TypeElement) {
            if(!e.getModifiers().contains(Modifier.PUBLIC))return false;
            e=e.getEnclosingElement();
        }
        return true;
    }
    public static void main(String[] args) throws Exception {
        Path jar=Path.of(args[0]),archive=Path.of(args[1]),output=Path.of(args[2]);
        JavaCompiler compiler=ToolProvider.getSystemJavaCompiler();
        Map<String,List<Map<String,Object>>> anchors=new TreeMap<>();
        Map<String,Map<String,Object>> types=new TreeMap<>();
        int[] sourceFiles={0};
        try(ZipFile zip=new ZipFile(archive.toFile())) {
            var names=zip.stream().map(ZipEntry::getName).filter(n->n.endsWith(".java")).sorted().toList();
            for(String name:names) {
                byte[] raw=zip.getInputStream(zip.getEntry(name)).readAllBytes();
                String digest=hash(raw);sourceFiles[0]++;
                JavacTask task=(JavacTask)compiler.getTask(null,null,null,List.of("-proc:none"),null,
                    List.of(new Source(name,new String(raw,StandardCharsets.UTF_8))));
                DocTrees docs=DocTrees.instance(task);
                for(CompilationUnitTree unit:task.parse())new TreePathScanner<Void,String>() {
                    Map<String,Object> anchor(Tree n) {
                        var result=new LinkedHashMap<String,Object>();
                        result.put("source_file",name);
                        result.put("line",unit.getLineMap().getLineNumber(docs.getSourcePositions().getStartPosition(unit,n)));
                        result.put("source_sha256",digest);
                        result.put("has_javadoc",docs.getDocCommentTree(getCurrentPath())!=null);
                        return result;
                    }
                    @Override public Void visitClass(ClassTree n,String parent) {
                        if(n.getSimpleName().length()==0)return null;
                        String owner=(parent==null?unit.getPackageName().toString():parent)+"."+n.getSimpleName();
                        types.put(owner,anchor(n));return super.visitClass(n,owner);
                    }
                    @Override public Void visitMethod(MethodTree n,String owner) {
                        String params=n.getParameters().stream().map(v->simple(v.getType().toString())).reduce((a,b)->a+","+b).orElse("");
                        anchors.computeIfAbsent(owner+"#"+n.getName()+"("+params+")",k->new ArrayList<>()).add(anchor(n));
                        return null;
                    }
                    @Override public Void visitVariable(VariableTree n,String owner) {
                        anchors.computeIfAbsent(owner+"#"+n.getName(),k->new ArrayList<>()).add(anchor(n));return null;
                    }
                }.scan(unit,null);
            }
        }
        DiagnosticCollector<JavaFileObject> diagnostics=new DiagnosticCollector<>();
        List<Map<String,Object>> rows=new ArrayList<>();
        List<Map<String,Object>> publicTypes=new ArrayList<>();
        List<String> unresolved=new ArrayList<>();
        try(StandardJavaFileManager fm=compiler.getStandardFileManager(diagnostics,null,StandardCharsets.UTF_8)) {
            JavacTask task=(JavacTask)compiler.getTask(null,fm,diagnostics,
                List.of("-proc:none","-classpath",jar.toString()),null,List.of(new Source("CatalogProbe.java","final class CatalogProbe {}")));
            task.parse();task.analyze();
            var elements=task.getElements();
            for(var entry:types.entrySet()) {
                String owner=entry.getKey();TypeElement type=elements.getTypeElement(owner);
                if(type==null){unresolved.add(owner);continue;}
                if(!accessible(type))continue;
                var t=new LinkedHashMap<String,Object>(entry.getValue());
                t.put("name",owner);t.put("kind",type.getKind().name());
                t.put("superclass",type.getSuperclass().toString());
                t.put("interfaces",type.getInterfaces().stream().map(Object::toString).toList());
                publicTypes.add(t);
                for(Element member:type.getEnclosedElements()) {
                    if(!member.getModifiers().contains(Modifier.PUBLIC))continue;
                    if(!Set.of(ElementKind.METHOD,ElementKind.CONSTRUCTOR,ElementKind.FIELD,ElementKind.ENUM_CONSTANT).contains(member.getKind()))continue;
                    String key=owner+"#"+member.getSimpleName();
                    if(member instanceof ExecutableElement) {
                        key+="("+((ExecutableElement)member).getParameters().stream().map(p->simple(p.asType().toString())).reduce((a,b)->a+","+b).orElse("")+")";
                    }
                    var row=new LinkedHashMap<String,Object>();
                    row.put("id",owner+"#"+member);row.put("owner",owner);
                    row.put("name",member.getSimpleName().toString());row.put("kind",member.getKind().name());
                    row.put("modifiers",member.getModifiers().stream().map(Object::toString).sorted().toList());
                    row.put("value_type",member instanceof ExecutableElement?((ExecutableElement)member).getReturnType().toString():member.asType().toString());
                    row.put("parameter_types",member instanceof ExecutableElement?((ExecutableElement)member).getParameters().stream().map(p->p.asType().toString()).toList():List.of());
                    var candidates=anchors.getOrDefault(key,List.of());
                    row.put("source_candidates",candidates);
                    row.put("source_match",candidates.size()==1?"unique_signature_anchor":candidates.isEmpty()?"no_exact_source_anchor":"ambiguous_source_anchor");
                    rows.add(row);
                }
            }
        }
        if(diagnostics.getDiagnostics().stream().anyMatch(d->d.getKind()==Diagnostic.Kind.ERROR))throw new IllegalStateException(diagnostics.getDiagnostics().toString());
        rows.sort(Comparator.comparing(r->r.get("id").toString()));
        var result=new LinkedHashMap<String,Object>();
        result.put("schema_version",1);result.put("game_jar_sha256",hash(Files.readAllBytes(jar)));
        result.put("source_archive_sha256",hash(Files.readAllBytes(archive)));result.put("source_files",sourceFiles[0]);
        result.put("public_types",publicTypes);result.put("members",rows);result.put("unresolved_source_types",unresolved);
        result.put("warning","Offline declaration candidates only. Public enclosing types and member access are compiler checked. No purity, safe getter, live reachability, thread, units, runtime validation or official stability contract is inferred. Inherited members are declared under their owner. Missing/ambiguous anchors remain explicit; signatures are not proof of source/binary equivalence. No method bodies, Javadoc text or game values are included.");
        Files.createDirectories(output.toAbsolutePath().getParent());
        Files.writeString(output,JsonWriter.encode(result),StandardCharsets.UTF_8);
        System.out.println("Catalog: "+publicTypes.size()+" public types; "+rows.size()+" public declared members; "+unresolved.size()+" unresolved source types");
    }
}
