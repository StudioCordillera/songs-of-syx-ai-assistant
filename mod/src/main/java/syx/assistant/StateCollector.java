package syx.assistant;

import game.GAME;
import game.VERSION;
import game.faction.FResources.RTYPE;
import game.time.TIME;
import init.paths.PATHS;
import init.race.RACES;
import init.race.Race;
import init.resources.RESOURCE;
import init.resources.RESOURCES;
import init.tech.TECH;
import init.tech.TECHS;
import init.type.HCLASS;
import init.type.HCLASSES;
import settlement.entity.ENTITY;
import settlement.entity.humanoid.Humanoid;
import settlement.main.SETT;
import settlement.room.main.RoomBlueprintIns;
import settlement.room.main.RoomInstance;
import settlement.stats.STATS;
import settlement.stats.stat.STAT;
import settlement.stats.stat.StatCollection;
import java.time.Instant;
import java.util.*;

/** All game reads happen on the simulation thread; returned values are detached DTOs. */
public final class StateCollector {
    public static final String[] DOMAINS = {"population", "resources", "production", "employment", "services",
        "housing", "health", "law", "happiness", "research", "trade", "diplomacy", "military", "world", "map", "entities", "events", "settings"};
    private static List<Object> referenceCache;
    public static void clearReferenceCache() { referenceCache=null; }
    private static String helpText(CharSequence text) { return text==null?"":text.toString(); }
    private static List<Object> references() {
        if(referenceCache!=null) return referenceCache;
        List<Object> result=new ArrayList<>();
        for(RESOURCE resource:RESOURCES.ALL()) result.add(object("id","resource:"+resource.key,"category","resource",
            "title",resource.name.toString(),"text",helpText(resource.desc),"origin","init.resources.RESOURCE: "+resource.key));
        for(TECH technology:TECHS.ALL()) result.add(object("id","technology:"+technology.key,"category","technology",
            "title",technology.name().toString(),"text",helpText(technology.desc()),"origin","init.tech.TECH: "+technology.key));
        for(STAT stat:STATS.all()) result.add(object("id","stat:"+stat.index(),"category","stat",
            "title",stat.info().name.toString(),"text",helpText(stat.info().desc),"origin","settlement.stats.stat.STAT: "+stat.key(),"stat_id",stat.index(),"individual_getter_available",stat.hasIndu() && stat.indu()!=null));
        referenceCache=result; return result;
    }
    static Map<String,Object> individualStat(Humanoid h,STAT stat) {
            Map<String,Object> row=object("stat_id",stat.index(),"key",stat.key(),"reference_id","stat:"+stat.index(),
                "unit","raw game integer; semantic units not established");
            try {
                util.data.INT_O<settlement.stats.Induvidual> getter=stat.indu();
                if(getter==null) throw new IllegalStateException("No individual getter");
                row.put("value",getter.get(h.indu()));row.put("min",getter.min(h.indu()));row.put("max",getter.max(h.indu()));
                row.put("coverage","partial");
            } catch(RuntimeException error) {
                row.put("value",null);row.put("coverage","unavailable");row.put("reason",error.getClass().getSimpleName());
            }
        return row;
    }
    /** Detached relationship DTOs; each public getter failure remains distinct from an absent assignment. */
    static Map<String,Object> personRelationships(Humanoid h) {
        Map<String,Object> result=object("coverage","partial","scope","instantiated_settlement_scene",
            "reason","Recorded assignments only, not current activity or UI selection. IDs are scene/session scoped; no private AI, complete history or home occupancy is inferred.");
        try {
            settlement.room.main.RoomInstance room=STATS.WORK().EMPLOYED.get(h);
            result.put("workplace",object("available",true,"data",room==null?null:object(
                "room_id",room.index(),"blueprint_id",room.blueprint().key,"name",room.name().toString(),
                "anchor_tile_x",room.mX(),"anchor_tile_y",room.mY())));
        } catch(RuntimeException error) {result.put("workplace",object("available",false,"data",null,"reason",error.getClass().getSimpleName()));}
        try {
            settlement.room.main.RoomBlueprintImp profession=STATS.WORK().profession.get(h.indu());
            result.put("profession",object("available",true,"data",profession==null?null:object("blueprint_id",profession.key)));
        } catch(RuntimeException error) {result.put("profession",object("available",false,"data",null,"reason",error.getClass().getSimpleName()));}
        try {
            snake2d.util.datatypes.COORDINATE home=STATS.HOME().GETTER.hCoo(h);
            result.put("home_assignment",object("available",true,"data",home==null?null:object("tile_x",home.x(),"tile_y",home.y())));
        } catch(RuntimeException error) {result.put("home_assignment",object("available",false,"data",null,"reason",error.getClass().getSimpleName()));}
        try {
            game.battle.div.Div div=h.division();
            result.put("division",object("available",true,"data",div==null?null:object("division_id",(int)div.index(),
                "army_division_index",(int)div.indexArmy(),"side",div.player()?"player":"enemy")));
        } catch(RuntimeException error) {result.put("division",object("available",false,"data",null,"reason",error.getClass().getSimpleName()));}
        return result;
    }
    private static Map<String,Object> selectedSubject() {
        if(!view.main.VIEW.existTemp() || !view.main.VIEW.s().isActive()) return null;
        Humanoid h=view.main.VIEW.s().ui.subjects.current();
        if(h==null || h.isRemoved()) return null;
        settlement.stats.Induvidual individual=h.indu();
        List<Object> stats=new ArrayList<>();int unsupported=0;
        for(STAT stat:STATS.all()) {
            if(!stat.hasIndu()) { unsupported++;continue; }
            stats.add(individualStat(h,stat));
        }
        return object("entity_id",h.id(),"race_id",h.race().key,"class_id",individual.clas().key,"type_id",individual.hType().key,
            "tile_x",h.tc().x(),"tile_y",h.tc().y(),"relationships",personRelationships(h),"stats",stats,"unsupported_stat_count",unsupported,
            "scope","underlying settlement subject panel; may be obscured by overlays or hidden UI",
            "coverage","partial","reason","Named statistics advertising hasIndu() only; not every attribute, history or private AI field. Independent of the first-1000 entity list.");
    }
    private static Map<String,Object> sceneArmy(String side,game.battle.Army army) {
        List<Object> divisions=new ArrayList<>();
        for(game.battle.div.Div div:army.divisions()) {
            int present=div.menNrOf();int configured=div.info.men();
            if(present<=0 && configured<=0)continue;
            Map<String,Object> row=object("division_id",(int)div.index(),"army_division_index",(int)div.indexArmy(),
                "name",div.info.name().toString(),"present_men",present,"configured_men",configured);
            try {
                game.battle.thread.status.DivStatus status=div.status();
                row.put("engine_engagement_flag",status.isFighting());
                double morale=div.morale();row.put("morale_raw",Double.isFinite(morale)?morale:null);
                row.put("race_id",div.race()==null?null:div.race().key);row.put("coverage","partial");
            }catch(RuntimeException error){row.put("coverage","unavailable");row.put("reason",error.getClass().getSimpleName());}
            divisions.add(row);
        }
        return object("side",side,"men",army.men(),"divisions",divisions,
            "scope","Currently instantiated settlement/battlefield army, not every campaign/world army",
            "status_note","engine_engagement_flag is the public DivStatus engagement flag from the latest published battle-worker buffer; it may lag simulation or remain stale when battle workers pause (including conclusion), and does not cover every form of damage/projectile activity",
            "units_note","Men are counts. configured_men minus present_men is not a general casualty measure. Morale is the raw game factor; range and interpretation are not established.");
    }
    private StateCollector() {}
    public static Map<String,Object> object(Object... pairs) {
        Map<String,Object> m = new LinkedHashMap<>();
        for (int i=0; i<pairs.length; i+=2) m.put((String)pairs[i], pairs[i+1]);
        return m;
    }
    private static Map<String,Object> domain(Object data, String reason) {
        return object("coverage", "partial", "reason", reason, "data", data);
    }
    public static Map<String,Object> envelope(String session, long sequence, boolean loaded) {
        Map<String,Object> domains = new LinkedHashMap<>();
        for (String d: DOMAINS) domains.put(d, object("coverage", "unavailable", "reason", "Not collected", "data", null));
        List<String> mods = new ArrayList<>();
        if (PATHS.inited()) for (init.paths.ModInfo m: PATHS.currentMods()) mods.add(m.path);
        return object("schema_version", 1, "session_id", session, "snapshot_id", session+":"+sequence,
            "game_version", VERSION.VERSION_STRING, "tick", loaded ? Math.max(0, GAME.updateI()) : 0,
            "captured_at", Instant.now().toString(), "game_loaded", loaded, "demo", false,
            "mods", mods, "domains", domains);
    }
    @SuppressWarnings("unchecked")
    public static Map<String,Object> collect(String session, long sequence) {
        Map<String,Object> result = envelope(session, sequence, true);
        Map<String,Object> domains = (Map<String,Object>) result.get("domains");
        Map<String,Object> scene=UiContextCollector.scene();result.put("scene",scene);
        // Each collector fails independently; failed values stay unavailable, never become zero.
        run(domains, "population", () -> {
            List<Object> rows = new ArrayList<>();
            for (Race race: RACES.all()) for (HCLASS cl: HCLASSES.ALL())
                rows.add(object("race_id", race.key, "class_id", cl.key, "count", STATS.POP().POP.data(cl).get(race)));
            return object("total", STATS.POP().POP.data().get(null), "by_race_class", rows, "unit", "people");
        }, "Settlement population totals and race/class counts; not individual histories.");
        run(domains, "resources", () -> {
            List<Object> rows = new ArrayList<>();
            for (RESOURCE r: RESOURCES.ALL()) rows.add(object("id", r.key, "name", r.name.toString(),
                "owned", r.owned(), "stockpile_stored", SETT.ROOMS().STOCKPILE.tally().amount.total(r),
                "stockpile_capacity", SETT.ROOMS().STOCKPILE.tally().space.total(r), "unit", "resource units"));
            return object("stockpiles", rows,"field_definitions",object(
                "owned",object("unit","resource units","scope","mixed_scene_logistics_and_player_trade_promises",
                    "definition","Game RESOURCE.owned(): reservable warehouse/hauler goods plus import/export/station goods and incoming station goods, minus player trade promises; not a warehouse-only count",
                    "source","init/resources/RESOURCE.java:537"),
                "stockpile_stored",object("unit","resource units","scope","instantiated_settlement_scene","source","SETT.ROOMS().STOCKPILE.tally().amount.total(resource)"),
                "stockpile_capacity",object("unit","resource units","scope","instantiated_settlement_scene","source","SETT.ROOMS().STOCKPILE.tally().space.total(resource)")));
        }, "Owned resources and warehouse totals; excludes per-crate and in-transit breakdowns.");
        run(domains, "production", () -> {
            List<Object> rows = new ArrayList<>();
            for (RESOURCE r: RESOURCES.ALL()) {
                Map<String,Object> flow = new LinkedHashMap<>();
                for (RTYPE t: RTYPE.values()) flow.put(t.name(), object("in_current_day", GAME.player().res().in(t).get(r.tr()),
                    "out_current_day", GAME.player().res().out(t).get(r.tr())));
                rows.add(object("id", r.key, "flows", flow));
            }
            return object("resources", rows, "unit", "resource units", "period", "current history bucket (game day)");
        }, "Resource ledger categories; not recipe throughput forecasts or per-room production.");
        run(domains, "employment", () -> {
            List<Object> rows = new ArrayList<>();
            for (RoomBlueprintIns<?> bp: SETT.ROOMS().ins()) for (RoomInstance room: bp.all()) {
                if (bp.employment() == null) continue;
                if (room.employees() == null) continue;
                rows.add(object("id", bp.key+":"+room.mX()+":"+room.mY(), "blueprint_id", bp.key,
                    "name", room.name().toString(), "tile_x", room.mX(), "tile_y", room.mY(),
                    "active", room.active(), "employed", room.employees().employed(), "needed", room.employees().needed(),
                    "target", room.employees().target(), "capacity", room.employees().max(), "unit", "workers"));
            }
            return object("rooms", rows);
        }, "Room workforce counts/targets; job assignment histories are not collected.");
        run(domains, "research", () -> {
            List<Object> rows = new ArrayList<>();
            for (TECH t: TECHS.ALL()) rows.add(object("id", t.key, "name", t.name().toString(), "level", GAME.player().tech().level(t), "max_level", t.levelMax));
            return object("technologies", rows);
        }, "Technology levels; currencies and unlock dependencies are not collected.");
        run(domains, "entities", () -> {
            List<Object> rows = new ArrayList<>();
            int total = 0;
            for (ENTITY e: SETT.ENTITIES().getAllEnts()) {
                if (e == null || e.isRemoved()) continue;
                total++;
                if (rows.size() >= 1000) continue;
                Map<String,Object> row = object("id", e.id(), "type", e.getClass().getSimpleName(), "tile_x", e.tc().x(), "tile_y", e.tc().y());
                if (e instanceof Humanoid) row.put("race_id", ((Humanoid)e).race().key);
                rows.add(row);
            }
            return object("items", rows, "total", total, "truncated", total>1000,"selected_subject",selectedSubject());
        }, "First 1000 live entity IDs/types/positions plus selected subject named individual statistics, independent of list truncation; not all attributes or private AI state.");
        run(domains, "trade", () -> {
            List<Object> rows=new ArrayList<>();
            for(RESOURCE r: RESOURCES.ALL()) rows.add(object("id",r.key,
                "imported_units_current_day",GAME.player().trade.unitsImported.get(r.tr()),
                "exported_units_current_day",GAME.player().trade.unitsExported.get(r.tr())));
            return object("resources",rows,"period","current game-day bucket","unit","resource units");
        }, "Import/export ledger totals; not pending shipments, price quotes or trading policy.");
        run(domains, "diplomacy", () -> {
            List<Object> rows=new ArrayList<>();
            for(game.faction.Faction f: game.faction.FACTIONS.active()) {
                if(f==GAME.player()) continue;
                game.faction.diplomacy.DipStance stance=game.faction.diplomacy.DIP.get(GAME.player(),f);
                rows.add(object("id",f.index(),"name",f.name.toString(),"stance_id",stance.key(),"stance",stance.name.toString()));
            }
            return object("factions",rows);
        }, "Current diplomatic stances; not treaties, relationship factors or hidden intentions.");
        run(domains, "world", () -> {
            List<Object> rows=new ArrayList<>();
            for(world.map.regions.Region region: world.WORLD.REGIONS().active()) rows.add(object(
                "id",region.index(),"name",region.info.name().toString(),"x",region.cx(),"y",region.cy(),
                "faction_id",region.faction()==null?null:region.faction().index(),"besieged",region.besieged()));
            return object("width",world.WORLD.TWIDTH(),"height",world.WORLD.THEIGHT(),"regions",rows);
        }, "Region identities, owners and siege flags; not complete regional economy or map tiles.");
        run(domains, "events", () -> {
            List<Object> definitions=new ArrayList<>();
            for(game.events.EVENTS.EventResource e: GAME.events().all()) definitions.add(e.key);
            game.event.engine.Event current=GAME.EVENT().current();
            return object("registered_event_types",definitions,"current_scripted_event_id",current==null?null:current.key,
                "current_scripted_event_elapsed_seconds",GAME.EVENT().timeElapsed());
        }, "Registered event types and current scripted-event ID only; no prediction or complete incident history.");
        run(domains, "settings", () -> object("paused", GAME.SPEED.isPaused(), "speed_target", GAME.SPEED.speedTarget(),
            "game_seconds", TIME.currentSecond(), "seconds_per_day", TIME.secondsPerDay()), "Clock/speed only; not all game settings.");
        run(domains, "map", () -> object("width", SETT.TWIDTH, "height", SETT.THEIGHT, "coordinate_unit", "settlement tiles",
            "on_demand_tool","query_live_tiles","tile_fields",Arrays.asList("terrain","floor","room","minerals","path")),
            "Dimensions and supported on-demand tile projections; tile rows require bounded spatial queries and are not included in this snapshot.");
        // Preserve every public stat by collection without guessing its meaning or normalized units.
        Map<String,String[]> groups = new LinkedHashMap<>();
        groups.put("services", new String[]{"SERVICE", "ACCESS", "NEEDS"});
        groups.put("housing", new String[]{"HOME"}); groups.put("health", new String[]{"DISEASE", "ENV", "FOOD"});
        groups.put("law", new String[]{"LAW"}); groups.put("happiness", new String[]{"ALL"});
        groups.put("military", new String[]{"BATTLE"});
        for (Map.Entry<String,String[]> group: groups.entrySet()) run(domains, group.getKey(), () -> {
            List<Object> rows = new ArrayList<>();
            for (StatCollection c: STATS.COLLECTIONS()) {
                boolean include = Arrays.asList(group.getValue()).contains("ALL") || Arrays.asList(group.getValue()).contains(c.key);
                if (!include) continue;
                for (STAT s: c.all()) {
                    List<Object> classes = new ArrayList<>();
                    for (HCLASS cl: HCLASSES.ALL()) {
                        try {
                            double normalized=s.data(cl).getD(null);
                            classes.add(object("class_id",cl.key,"raw",s.data(cl).get(null),
                                "normalized",Double.isFinite(normalized)?normalized:null));
                        } catch(Exception e) { classes.add(object("class_id",cl.key,"unavailable",e.getClass().getSimpleName())); }
                    }
                    rows.add(object("collection",c.key,"id",s.key(),"name",s.info().name.toString(),"by_class",classes,
                        "divider",s.dataDivider(),"unit","game-defined stat; inspect meaning before interpreting"));
                }
            }
            Map<String,Object> data=object("statistics", rows);
            if(group.getKey().equals("military"))data.put("scene_armies",Arrays.asList(sceneArmy("player",GAME.ARMIES().player()),sceneArmy("enemy",GAME.ARMIES().enemy())));
            return data;
        }, group.getKey().equals("military")?"Public battle aggregates and scene division rows; not every campaign army, private order state or combat history":"Public aggregate statistics only; no causal/historical completeness is claimed.");
        Set<String> sceneDomains=Set.of("population","resources","employment","services","housing","health","law","happiness","military","map","entities");
        for(String key:DOMAINS) {
            Map<String,Object> record=(Map<String,Object>)domains.get(key);
            String scope=sceneDomains.contains(key)?"instantiated_settlement_scene":
                Set.of("production","trade","research","diplomacy").contains(key)?"campaign_player_or_faction":"game_or_world";
            if(key.equals("resources"))scope="mixed_scene_logistics_and_player_trade_promises";
            record.put("scope",scope);
            if(sceneDomains.contains(key) && !SETT.exists())domains.put(key,object("coverage","unavailable","data",null,"scope",scope,
                "reason","No instantiated settlement scene; new-game preparation data is not a live city"));
        }
        if(!world.WORLD.GEN().isDone) for(String key:Set.of("world","production","trade","research","diplomacy","events")) {
            Map<String,Object> previous=(Map<String,Object>)domains.get(key);
            domains.put(key,object("coverage","unavailable","data",null,"scope",previous.get("scope"),
                "reason","World generation is not complete; campaign/economy placeholders are not a completed world"));
        }
        try { result.put("ui_context",UiContextCollector.collect()); }
        catch(Exception e) { result.put("ui_context",object("available",false,"coverage","unavailable","reason",e.getClass().getSimpleName()+": "+e.getMessage())); }
        result.put("references",references());
        return result;
    }
    private interface Reader { Object read() throws Exception; }
    private static void run(Map<String,Object> domains, String key, Reader reader, String reason) {
        try { domains.put(key, domain(reader.read(), reason)); }
        catch (Exception e) { domains.put(key, object("coverage", "unavailable", "reason", e.getClass().getSimpleName()+": "+e.getMessage(), "data", null)); }
    }
}
