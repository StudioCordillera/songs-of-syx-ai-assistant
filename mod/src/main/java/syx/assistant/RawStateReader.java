package syx.assistant;

import java.lang.reflect.*;
import java.util.*;
import java.util.function.Supplier;
import snake2d.util.sets.LIST;
import static syx.assistant.StateCollector.object;

/** Explicit, read-only field exploration of game-owned objects. Never invokes arbitrary methods. */
public final class RawStateReader {
    private final Map<String,Supplier<Object>> roots;
    private int budget;
    public RawStateReader() {
        roots=new LinkedHashMap<>();
        roots.put("game",()->game.GAME.class);
        roots.put("settlement",()->settlement.main.SETT.CITY());
        roots.put("world",()->game.GAME.world());
        roots.put("player",()->game.GAME.player());
        roots.put("factions",()->game.faction.FACTIONS.active());
        roots.put("stats",()->settlement.stats.STATS.class);
        roots.put("resources",()->init.resources.RESOURCES.ALL());
        roots.put("races",()->init.race.RACES.all());
        roots.put("technologies",()->init.tech.TECHS.ALL());
        roots.put("clock",()->game.time.TIME.class);
        roots.put("events",()->game.GAME.events());
    }
    public RawStateReader(Map<String,Supplier<Object>> roots) { this.roots=roots; }
    private void spend() { if(--budget<0) throw new IllegalArgumentException("Raw query budget exceeded; narrow fields/depth"); }
    @SuppressWarnings("unchecked")
    public Object execute(Object request) {
        budget=10000;
        if(!(request instanceof List<?>)) throw new IllegalArgumentException("reads must be an array");
        List<?> reads=(List<?>)request;
        if(reads.isEmpty()) return object("roots",new ArrayList<>(roots.keySet()),"path_syntax","JSON pointer of Java fields; /@items for collections; /0 for an array/list index",
            "note","Fields are version-specific. Methods, native handles and non-game implementation details are not callable/readable.");
        if(reads.size()>20) throw new IllegalArgumentException("At most twenty reads per live query");
        List<Object> results=new ArrayList<>();
        for(Object value:reads) {
            if(!(value instanceof Map<?,?>)) throw new IllegalArgumentException("Each read must be an object");
            Map<String,Object> read=(Map<String,Object>)value;
            if(!Set.of("name","root","path","depth","offset","limit","fields").containsAll(read.keySet())) throw new IllegalArgumentException("Unknown raw query option");
            String root=(String)read.get("root");Supplier<Object> supplier=roots.get(root);
            if(supplier==null) throw new IllegalArgumentException("Unknown game root");
            int depth=integer(read,"depth",0),offset=integer(read,"offset",0),limit=integer(read,"limit",30);
            if(depth<0||depth>4||offset<0||limit<1||limit>100) throw new IllegalArgumentException("depth 0..4; offset >=0; limit 1..100");
            String path=(String)read.getOrDefault("path","");
            Object target=resolve(supplier.get(),path);
            Object data;
            if(read.containsKey("fields")) {
                if(!(read.get("fields") instanceof Map<?,?>)) throw new IllegalArgumentException("fields must map aliases to pointers");
                Map<String,Object> projected=new LinkedHashMap<>();
                Map<String,Object> fields=(Map<String,Object>)read.get("fields");
                if(fields.size()>50) throw new IllegalArgumentException("At most fifty projected fields");
                for(Map.Entry<String,Object> field:fields.entrySet()) projected.put(field.getKey(), export(resolve(target,(String)field.getValue()),depth,offset,limit,new IdentityHashMap<>()));
                data=projected;
            } else data=export(target,depth,offset,limit,new IdentityHashMap<>());
            results.add(object("name",read.get("name"),"root",root,"path",path,"data",data));
        }
        return object("reads",results,"consistency","All field reads executed on one game update thread; inspect enclosing tick.");
    }
    private int integer(Map<String,Object> m,String key,int fallback) {
        Object value=m.get(key);if(value==null)return fallback;
        if(!(value instanceof Number)||((Number)value).doubleValue()!=((Number)value).intValue()) throw new IllegalArgumentException(key+" must be an integer");
        return ((Number)value).intValue();
    }
    private static boolean allowed(Class<?> c) {
        String n=c.getName();
        return n.startsWith("game.")||n.startsWith("settlement.")||n.startsWith("world.")||n.startsWith("init.")||
            n.startsWith("util.data.")||n.startsWith("util.statistics.")||n.startsWith("util.keymap.")||n.startsWith("util.info.")||
            n.startsWith("snake2d.util.sets.");
    }
    private Object resolve(Object value,String path) {
        if(path.isEmpty()) return value;
        if(!path.startsWith("/")||path.length()>1000) throw new IllegalArgumentException("Use a JSON pointer field path");
        for(String encoded:path.substring(1).split("/",-1)) {
            spend();String token=encoded.replace("~1","/").replace("~0","~");
            if(value==null) throw new IllegalArgumentException("Path crosses null: "+path);
            if(token.equals("@items") && (value instanceof LIST<?> || value instanceof List<?> || value.getClass().isArray())) continue;
            if(token.equals("@size")) { value=size(value);continue; }
            if(value.getClass().isArray() || value instanceof LIST<?> || value instanceof List<?>) {
                if(!token.matches("0|[1-9][0-9]*")) throw new IllegalArgumentException("Expected collection index");
                int index=Integer.parseInt(token);if(index>=size(value)) throw new IllegalArgumentException("Collection index outside current bounds");
                value=item(value,index);continue;
            }
            Class<?> cls=value instanceof Class<?>?(Class<?>)value:value.getClass();
            if(!allowed(cls)) throw new IllegalArgumentException("Not a game-state object: "+cls.getName());
            Field field=find(cls,token);
            boolean isStatic=Modifier.isStatic(field.getModifiers());
            if(field.isSynthetic() || (value instanceof Class<?> && !isStatic)) throw new IllegalArgumentException("Not a readable field");
            if(!field.trySetAccessible()) throw new IllegalArgumentException("Field is inaccessible");
            try { value=field.get(isStatic?null:value); } catch(IllegalAccessException e) { throw new IllegalArgumentException("Field is inaccessible",e); }
        }
        return value;
    }
    private static Field find(Class<?> cls,String name) {
        while(cls!=null && allowed(cls)) {
            try{return cls.getDeclaredField(name);}catch(NoSuchFieldException e){cls=cls.getSuperclass();}
        }
        throw new IllegalArgumentException("Unknown game field: "+name);
    }
    private static int size(Object v) {
        if(v.getClass().isArray())return Array.getLength(v);if(v instanceof LIST<?>)return ((LIST<?>)v).size();
        if(v instanceof List<?>)return ((List<?>)v).size();throw new IllegalArgumentException("Not an indexed collection");
    }
    private static Object item(Object v,int i) { if(v.getClass().isArray())return Array.get(v,i);if(v instanceof LIST<?>)return ((LIST<?>)v).get(i);return ((List<?>)v).get(i); }
    private Object export(Object value,int depth,int offset,int limit,IdentityHashMap<Object,Boolean> seen) {
        spend();
        if(value==null || value instanceof Boolean || value instanceof CharSequence || value instanceof Character) return value==null?null:value instanceof Character || value instanceof CharSequence?value.toString():value;
        if(value instanceof Number) return Double.isFinite(((Number)value).doubleValue())?value:null;
        if(value instanceof Enum<?>)return ((Enum<?>)value).name();
        if(seen.put(value,Boolean.TRUE)!=null) return object("$cycle",true,"$type",value.getClass().getName());
        if(value.getClass().isArray() || value instanceof LIST<?> || value instanceof List<?>) {
            int size=size(value);List<Object> items=new ArrayList<>();
            for(int i=offset;i<Math.min(size,(long)offset+limit);i++)items.add(export(item(value,i),Math.max(0,depth-1),0,limit,seen));
            return object("$type",value.getClass().getName(),"size",size,"offset",offset,"next_offset",(long)offset+limit<size?offset+limit:null,"items",items);
        }
        Class<?> cls=value instanceof Class<?>?(Class<?>)value:value.getClass();
        if(!allowed(cls))return object("$type",cls.getName(),"$blocked","Non-game/native implementation object");
        List<Field> fields=new ArrayList<>();
        for(Class<?> c=cls;c!=null && allowed(c);c=c.getSuperclass()) for(Field f:c.getDeclaredFields())
            if(!f.isSynthetic() && (value instanceof Class<?>?Modifier.isStatic(f.getModifiers()):!Modifier.isStatic(f.getModifiers()))) fields.add(f);
        fields.sort(Comparator.comparing(Field::getName));List<Object> definitions=new ArrayList<>();Map<String,Object> values=new LinkedHashMap<>();
        for(int i=offset;i<Math.min(fields.size(),(long)offset+limit);i++) {
            spend();Field f=fields.get(i);boolean readable=f.trySetAccessible();
            definitions.add(object("name",f.getName(),"type",f.getType().getTypeName(),"declared_in",f.getDeclaringClass().getName(),"readable",readable));
            if(depth>0 && readable) try { values.put(f.getName(),export(f.get(Modifier.isStatic(f.getModifiers())?null:value),depth-1,0,limit,seen)); }
                catch(IllegalAccessException e) { values.put(f.getName(),object("$unavailable",e.getClass().getSimpleName())); }
        }
        Map<String,Object> result=object("$type",cls.getName(),"fields",definitions,"field_count",fields.size(),"next_offset",(long)offset+limit<fields.size()?offset+limit:null);
        if(depth>0)result.put("values",values);return result;
    }
}
