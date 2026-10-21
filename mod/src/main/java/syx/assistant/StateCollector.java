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
        for(settlement.room.main.RoomBlueprint blueprint:SETT.ROOMS().all()) {
            if(!(blueprint instanceof settlement.room.main.RoomBlueprintImp))continue;
            var room=(settlement.room.main.RoomBlueprintImp)blueprint;
            result.add(object("id","room:"+room.key,"category","room","title",room.info.name.toString(),
                "text",helpText(room.info.desc),"origin","settlement.room.main.RoomBlueprintImp: "+room.key));
        }
        for(var currency:TECHS.COSTS())result.add(object("id","research_currency:"+currency.bo.key,
            "category","research_currency","title",currency.bo.name.toString(),"text",helpText(currency.bo.desc),
            "origin","init.tech.TechCurrency / game.boosting.Boostable: "+currency.bo.key));
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
    private static Object finiteFactor(double value) { return Double.isFinite(value)?value:null; }
    /** Stored employment factors only: never reports work, enumerates employees or refreshes a room. */
    private static Map<String,Object> roomEmployment() {
        if(!SETT.exists())return object("coverage","unavailable","scope","instantiated_settlement_scene",
            "reason","No instantiated settlement scene","rooms",null);
        List<Object> rows=new ArrayList<>(),failures=new ArrayList<>();
        int scanned=0,failed=0;boolean truncated=false;
        scan:for(RoomBlueprintIns<?> bp:SETT.ROOMS().ins())for(RoomInstance room:bp.all()) {
            if(scanned>=10000){truncated=true;break scan;}scanned++;
            try {
                if(bp.employment()==null || room.employees()==null)continue;
                if(rows.size()>=2000){truncated=true;break scan;}
                var staff=room.employees();
                Map<String,Object> factors=object("efficiency_stored_raw",finiteFactor(staff.efficiency()),
                    "proximity_stored_raw",finiteFactor(staff.proximity()),
                    "fetch_proximity_stored_raw",finiteFactor(staff.fetchProximity()),
                    "fetch_factor_applies",bp.employment().countInput(),
                    "combined_efficiency_raw",finiteFactor(staff.totEfficiency()));
                rows.add(object("id",bp.key+":"+room.mX()+":"+room.mY(),"room_id",room.index(),
                    "blueprint_id",bp.key,"reference_id","room:"+bp.key,"name",room.name().toString(),
                    "tile_x",room.mX(),"tile_y",room.mY(),"active",room.active(),
                    "employed",staff.employed(),"needed",staff.needed(),"target",staff.target(),
                    "capacity",staff.max(),"unit","workers","work_factors",factors));
            }catch(RuntimeException error) {
                failed++;if(failures.size()<10)failures.add(object("room_id",room.index(),"reason",error.getClass().getSimpleName()));
            }
        }
        return object("coverage","partial","scope","instantiated_settlement_scene","rooms",rows,
            "scanned_rooms",scanned,"failed_rooms",failed,"failure_samples",failures,"truncated",truncated,
            "row_limit",2000,"scan_room_limit",10000,"field_definitions",object(
                "room_id",object("definition","Public RoomInstance.index(), shared with person workplace and production flows in the same observation. Not a permanent campaign ID; indexes can be reused.",
                    "scope","instantiated_settlement_scene","source","settlement/room/main/Room.java:index()"),
                "work_factors",object("source","settlement/room/main/employment/RoomEmploymentIns.java:efficiency,proximity,fetchProximity,totEfficiency; RoomEmploymentSimple.java:countInput",
                    "units","Dimensionless raw getter factors, not worker counts, current productivity percentages or output per day. No range clamping; nonfinite values are null.",
                    "efficiency_stored_raw","Stored/smoothed work-report factor. Can reset to a default when staffing/activation changes; not instantaneous idle time or a staffing recommendation.",
                    "proximity_stored_raw","Stored travel-related factor; not tile distance, minutes or a current path/reachability test.",
                    "fetch_proximity_stored_raw","Stored fetch-related factor. Its presence does not prove that this room uses it; inspect fetch_factor_applies.",
                    "fetch_factor_applies","Blueprint countInput() flag selects whether the fetch factor participates in totEfficiency(). Not proof of input stock or active fetching.",
                    "combined_efficiency_raw","Public totEfficiency(): efficiency * proximity, additionally * fetchProximity only when countInput is true. Excludes room boosts, individual/race/technology bonuses and input supply. Does not establish current/future work duration; not a complete production multiplier or forecast.",
                    "periods","Stored values can be smoothed, defaulted or reset. Exact sample age/reporting interval is not exposed; no update/report/refresh method is invoked.")),
            "reason","Employing room instances only. Bounded stored workforce factors/counts, not every job, worker history, complete modifiers or throughput. Missing/skipped/failed rooms do not imply zero workforce.");
    }
    /** Stored city stockpile bookkeeping; no crate handles, refresh or reservation actions. */
    private static Map<String,Object> stockpileBookkeeping() {
        if(!SETT.exists() || SETT.WORLD_AREA().isBattle || !world.WORLD.GEN().isDone)
            return object("coverage","unavailable","scope","instantiated_city_stockpile_bookkeeping","rows",null,
                "reason","No completed instantiated campaign city; battlefield/setup defaults are not city stockpile bookkeeping.");
        List<Object> rows=new ArrayList<>(),failures=new ArrayList<>();
        int scanned=0,failed=0;boolean truncated=false;
        var tally=SETT.ROOMS().STOCKPILE.tally();
        for(RESOURCE resource:RESOURCES.ALL()) {
            if(scanned>=1000){truncated=true;break;}scanned++;
            try {
                int ri=resource.index();
                if(ri<0 || ri>=RESOURCES.ALL().size())throw new IllegalStateException("Resource index out of range");
                // Each entire resource row is emitted or omitted; never replace a failed getter with zero.
                rows.add(object("resource_id",resource.key,"reference_id","resource:"+resource.key,
                    "assigned_crates",tally.crates.total(ri),"stored_raw",tally.amount.total(ri),
                    "capacity_raw",tally.space.total(ri),"reserved_stored_raw",tally.amountReserved.total(ri),
                    "reserved_incoming_raw",tally.spaceReserved.total(ri)));
            } catch(RuntimeException error) {
                failed++;if(failures.size()<10)failures.add(object("resource_id",resource.key,"reason",error.getClass().getSimpleName()));
            }
        }
        return object("coverage","partial","scope","instantiated_city_stockpile_bookkeeping","rows",rows,
            "scanned_resources",scanned,"resource_count_total",RESOURCES.ALL().size(),"resource_limit",1000,"row_limit",1000,
            "failed_resources",failed,"failure_samples",failures,"truncated",truncated,
            "reason","Stored resource-specific warehouse tallies including reservations. Exact age, ground/in-transit goods, per-room/crate detail and future delivery/reachability are not established; missing rows are not zero.");
    }
    /** Fixed public recipe/ledger readers only. Never refresh buckets or retain game storage. */
    private static Map<String,Object> roomProduction() {
        if(!SETT.exists())return object("coverage","unavailable","scope","instantiated_settlement_scene",
            "reason","No instantiated settlement scene","flows",null);
        List<Object> flows=new ArrayList<>(),failures=new ArrayList<>();
        int scanned=0,failed=0,producers=0;boolean truncated=false;
        scan:for(RoomBlueprintIns<?> blueprint:SETT.ROOMS().ins())for(RoomInstance room:blueprint.all()) {
            if(scanned>=10000){truncated=true;break scan;}scanned++;
            if(!(room instanceof settlement.room.industry.module.ROOM_PRODUCER_INSTANCE))continue;
            var producer=(settlement.room.industry.module.ROOM_PRODUCER_INSTANCE)room;
            try {
                var industry=producer.industry();
                if(industry==null)throw new IllegalStateException("No current industry");
                int needed=industry.ins().size()+industry.outs().size();
                if(flows.size()+needed>2000){truncated=true;break scan;}
                List<Object> pending=new ArrayList<>();
                Object degradation=finiteFactor(room.getDegrade());
                for(String direction:Arrays.asList("input","output")) {
                    var resources=direction.equals("input")?industry.ins():industry.outs();
                    for(var resource:resources) {
                        double rate=resource.rate,day=resource.day.getD(producer);
                        pending.add(object("room_id",room.index(),"blueprint_id",blueprint.key,
                            "industry_id",industry.index(),"recipe_index",producer.industryI(),"direction",direction,
                            "resource_id",resource.resource.key,"reference_id","resource:"+resource.resource.key,
                            "room_reference_id","room:"+blueprint.key,"room_degradation_raw",degradation,
                            "base_rate_raw",Double.isFinite(rate)?rate:null,
                            "day_accumulator_raw",Double.isFinite(day)?day:null,
                            "previous_day_units",resource.dayPrev.get(producer),
                            "year_units",resource.year.get(producer),"previous_year_units",resource.yearPrev.get(producer)));
                    }
                }
                flows.addAll(pending);producers++;
            } catch(RuntimeException error) {
                failed++;
                if(failures.size()<10)failures.add(object("room_id",room.index(),"reason",error.getClass().getSimpleName()));
            }
        }
        return object("coverage","partial","scope","instantiated_settlement_scene","flows",flows,
            "scanned_rooms",scanned,"read_producer_rooms",producers,"failed_rooms",failed,"failure_samples",failures,
            "truncated",truncated,"row_limit",2000,"scan_room_limit",10000,
            "reason","Current recipe only for public ROOM_PRODUCER_INSTANCE rooms. Stored ledger buckets are not refreshed by this observer; configured rates and recorded quantities are not output forecasts or a complete service/production schema.");
    }
    /** Public ROOM_SERVICER counters only; no service finder, report or refresh calls. */
    private static Map<String,Object> roomServices() {
        if(!SETT.exists())return object("coverage","unavailable","scope","instantiated_settlement_scene",
            "reason","No instantiated settlement scene","rooms",null);
        List<Object> rows=new ArrayList<>(),failures=new ArrayList<>();
        int scanned=0,failed=0;boolean truncated=false;
        scan:for(RoomBlueprintIns<?> blueprint:SETT.ROOMS().ins())for(RoomInstance room:blueprint.all()) {
            if(scanned>=10000){truncated=true;break scan;}scanned++;
            if(!(room instanceof settlement.room.service.module.ROOM_SERVICER))continue;
            if(rows.size()>=2000){truncated=true;break scan;}
            try {
                var service=((settlement.room.service.module.ROOM_SERVICER)room).service();
                if(service==null)throw new IllegalStateException("No service counters");
                rows.add(object("room_id",room.index(),"blueprint_id",blueprint.key,"reference_id","room:"+blueprint.key,
                    "active",room.active(),"total_slots_raw",service.total(),"available_slots_raw",service.available(),
                    "reserved_slots_raw",service.reserved()));
            }catch(RuntimeException error) {
                failed++;if(failures.size()<10)failures.add(object("room_id",room.index(),"reason",error.getClass().getSimpleName()));
            }
        }
        return object("coverage","partial","scope","instantiated_settlement_scene","rooms",rows,
            "scanned_rooms",scanned,"failed_rooms",failed,"failure_samples",failures,"truncated",truncated,
            "row_limit",2000,"scan_room_limit",10000,
            "reason","ROOM_SERVICER instances only. Stored raw service-point counters, not people served per day, demand, reachability, citizen permissions or a complete service schema. Unimplemented room interfaces do not mean zero service.");
    }
    /** Configured cohort rules, not effective individual access or actual service visits. */
    private static Map<String,Object> servicePolicies() {
        if(!SETT.exists() || SETT.WORLD_AREA().isBattle || !world.WORLD.GEN().isDone)return object("coverage","unavailable",
            "scope","instantiated_city_service_configuration","service_types",new ArrayList<>(),"cohort_rules",new ArrayList<>(),
            "reason","No completed instantiated campaign city; battlefield/setup defaults are not city service policy.");
        List<Object> types=new ArrayList<>(),rules=new ArrayList<>(),failures=new ArrayList<>();
        var races=RACES.all();var classes=HCLASSES.ALL();
        if(races.size()>64 || classes.size()>64)return object("coverage","unavailable",
            "scope","instantiated_city_service_configuration","service_types",types,"cohort_rules",rules,
            "truncated",true,"reason","Race/class scan limit of 64 exceeded");
        int failed=0,scanned=0;boolean truncated=false;int cohortCount=races.size()*classes.size();
        for(var service:settlement.room.service.module.RoomServiceAccess.ALL()) {
            if(scanned>=256 || rules.size()+cohortCount>10000){truncated=true;break;}scanned++;
            try {
                var blueprint=service.room();var permission=service.stats().permission();
                List<Object> pending=new ArrayList<>();
                for(Race race:races)for(HCLASS cl:classes)pending.add(object("service_id",service.index(),
                    "blueprint_id",blueprint.key,"race_id",race.key,"class_id",cl.key,
                    "allowed_by_configured_rule",permission.is(init.type.HCLASS_RACE.clP(race,cl))));
                types.add(object("service_id",service.index(),"blueprint_id",blueprint.key,"reference_id","room:"+blueprint.key));
                rules.addAll(pending);
            }catch(RuntimeException error) {
                failed++;if(failures.size()<10)failures.add(object("service_id",service.index(),"reason",error.getClass().getSimpleName()));
            }
        }
        return object("coverage","partial","scope","instantiated_city_service_configuration","service_types",types,"cohort_rules",rules,
            "scanned_service_types",scanned,"failed_service_types",failed,"failure_samples",failures,"truncated",truncated,
            "service_type_limit",256,"rule_row_limit",10000,"race_scan_limit",64,"class_scan_limit",64,
            "cohorts_per_service_type",cohortCount,
            "reason","Registered RoomServiceAccess types, including types without built rooms. Configured race/class permission only; individual rules for nobles, tourists and children can differ. Not actual access, demand, visits, reachability or a complete eligibility decision. No permission setter or access request is invoked.");
    }
    /** Stored campaign resource-output accrual only; never refresh boosts or ship goods. */
    private static Map<String,Object> regionalOutputBookkeeping() {
        if(!world.WORLD.GEN().isDone)return object("coverage","unavailable","scope","campaign_world_regions",
            "rows",null,"schedules",null,"reason","No completed campaign world; setup defaults are not regional output observations.");
        List<Object> rows=new ArrayList<>(),schedules=new ArrayList<>(),failures=new ArrayList<>();
        List<RESOURCE> resources=new ArrayList<>();
        List<world.region.RDOutputs.RDResource> outputs=new ArrayList<>();
        int scannedResources=0,failedResources=0,scannedRegions=0,scannedCells=0,failedCells=0;
        boolean resourceTruncated=false,regionTruncated=false,cellTruncated=false;
        for(RESOURCE resource:RESOURCES.ALL()) {
            if(scannedResources>=1000){resourceTruncated=true;break;}scannedResources++;
            try {
                var tradable=init.trade.TR.get(resource);var output=world.region.RD.OUTPUT().get(tradable);
                if(output.res!=tradable)throw new IllegalStateException("Resource output identity mismatch");
                int days=output.daysUntilDailydelivery();
                if(days<0)throw new IllegalStateException("Negative configured day offset");
                schedules.add(object("resource_id",resource.key,"reference_id","resource:"+resource.key,
                    "days_until_configured_output",days));resources.add(resource);outputs.add(output);
            } catch(RuntimeException error) {
                failedResources++;if(failures.size()<10)failures.add(object("resource_id",resource.key,"reason",error.getClass().getSimpleName()));
            }
        }
        var active=world.WORLD.REGIONS().active();
        scan:for(var region:active) {
            if(scannedRegions>=1023){regionTruncated=true;break;}scannedRegions++;
            for(int i=0;i<resources.size();i++) {
                if(scannedCells>=10000){cellTruncated=true;break scan;}scannedCells++;
                RESOURCE resource=resources.get(i);
                try {
                    int value=outputs.get(i).yearlyAccumilation.get(region);
                    if(value<0)throw new IllegalStateException("Negative stored output counter");
                    rows.add(object("region_id",region.index(),"resource_id",resource.key,"reference_id","resource:"+resource.key,
                        "accrued_output_raw",value));
                } catch(RuntimeException error) {
                    failedCells++;if(failures.size()<10)failures.add(object("region_id",region.index(),
                        "resource_id",resource.key,"reason",error.getClass().getSimpleName()));
                }
            }
        }
        return object("coverage","partial","scope","campaign_world_regions","rows",rows,"schedules",schedules,
            "scanned_resources",scannedResources,"resource_count_total",RESOURCES.ALL().size(),"failed_resources",failedResources,
            "resource_limit",1000,"resource_truncated",resourceTruncated,
            "scanned_regions",scannedRegions,"region_count_total",active.size(),"region_limit",1023,"region_truncated",regionTruncated,
            "scanned_cells",scannedCells,"cell_limit",10000,"row_limit",10000,"failed_cells",failedCells,"cell_truncated",cellTruncated,
            "truncated",resourceTruncated || regionTruncated || cellTruncated,"failure_samples",failures,
            "field_definitions",object(
                "accrued_output_raw",object("definition","Stored resource-backed scheduled-output accrual (public yearlyAccumilation). Not inventory, annual delivered output, daily production or income. Ownership changes can reset it; exact age is not exposed.",
                    "unit","raw accrued resource items","scope","campaign_world_regions",
                    "source","RD.OUTPUT().get(TR.get(resource)).yearlyAccumilation.get(region); world/region/RDOutputs.java and updating/Shipper.java"),
                "days_until_configured_output",object("definition","Cyclic configured output-day offset, including a growable seasonal offset when present. Not actual departure/arrival ETA, shipping permission or guaranteed delivery.",
                    "unit","game days in the configured yearly cycle","scope","loaded_resource_output_schedule",
                    "source","world.region.RDOutputs.RDResource.daysUntilDailydelivery()")),
            "reason","Bounded resource-backed campaign accruals, including zero values. Whole failed cells/resource bindings are omitted; missing rows are unknown. Non-resource tradables, MONEY, boosts/forecasts, shipping actions and private update timers are excluded.");
    }
    /** Campaign regional counters, detached and bounded; never forces regional updates. */
    private static Map<String,Object> worldData() {
        List<Object> regions=new ArrayList<>(),population=new ArrayList<>(),failures=new ArrayList<>();
        var active=world.WORLD.REGIONS().active();var races=world.region.RD.RACES().all;
        boolean regionTruncated=false,populationTruncated=false;int failed=0;
        for(var region:active) {
            if(regions.size()>=1023){regionTruncated=true;break;}
            var faction=region.faction();
            Map<String,Object> row=object("id",region.index(),"name",region.info.name().toString(),
                "x",region.cx(),"y",region.cy(),"faction_id",faction==null?null:faction.index(),
                "player_owned",faction==GAME.player(),"besieged",region.besieged(),"capital",region.capitol(),
                "area_world_tiles",region.info.area(),"population_total",null,"population_coverage","unavailable");
            if(races.size()>64 || population.size()+races.size()>10000) {
                populationTruncated=true;row.put("population_reason","Regional race scan or population-row limit reached; no population inferred");
            } else try {
                int total=world.region.RD.RACES().population.get(region);
                List<Object> pending=new ArrayList<>();
                for(var race:races)pending.add(object("region_id",region.index(),"race_id",race.race.key,"population",race.pop.get(region)));
                population.addAll(pending);row.put("population_total",total);row.put("population_coverage","partial");
            } catch(RuntimeException error) {
                failed++;row.put("population_reason",error.getClass().getSimpleName());
                if(failures.size()<10)failures.add(object("region_id",region.index(),"reason",error.getClass().getSimpleName()));
            }
            regions.add(row);
        }
        Map<String,Object> output;
        try {output=regionalOutputBookkeeping();}
        catch(RuntimeException error){output=object("coverage","unavailable","scope","campaign_world_regions","rows",null,"schedules",null,"reason",error.getClass().getSimpleName());}
        return object("width",world.WORLD.TWIDTH(),"height",world.WORLD.THEIGHT(),"regions",regions,"regional_output_bookkeeping",output,
            "population_by_race",population,"region_count_total",active.size(),"region_truncated",regionTruncated,
            "region_limit",1023,"population_truncated",populationTruncated,"population_row_limit",10000,
            "race_scan_limit",64,"population_failed_regions",failed,"population_failure_samples",failures,
            "field_definitions",object(
                "regional_output_bookkeeping",output.get("field_definitions"),
                "population_total",object("definition","Stored regional population counter, not the instantiated settlement citizen count or a forecast.",
                    "unit","regional inhabitants","scope","campaign_world_regions","source","world.region.RD.RACES().population -> world/region/RData.java:get(Region)",
                    "availability","Null when demographic reads fail or are skipped by a reported cap; not zero."),
                "population_by_race",object("definition","Stored regional counts for public RDRaces.all entries (playable races in this installed build). Zero counts are retained; no hidden or non-playable race census is claimed.",
                    "unit","regional inhabitants","scope","campaign_world_regions","source","world/region/pop/RDRace.java:pop -> RData.get(Region)",
                    "relationships","region_id joins regions.id in the same observation. race_id is the installed Race.key; shared race identity does not make regional and settlement populations interchangeable.",
                    "limits","At most 64 race entries per region and 10000 population rows; a region is never split across the row cap. Inspect region population_coverage and population_truncated/failed counts."),
                "area_world_tiles",object("unit","world tiles","source","world/map/regions/RegionInfo.java:area()","definition","Stored area counted from region membership during map initialization; not settlement tiles or farmland area."),
                "capital",object("source","world/map/regions/Region.java:capitol()","definition","This region is its realm capital; false when there is no realm. It is not a UI-selection flag.")));
    }
    /** Read-only public city trade bookkeeping. No reservation/delivery/quote mutator is invoked. */
    private static Map<String,Object> tradePipeline() {
        if(!SETT.exists() || SETT.WORLD_AREA().isBattle)return object("coverage","unavailable",
            "scope","instantiated_city_trade","policies",new ArrayList<>(),"flows",new ArrayList<>(),
            "reason","No instantiated campaign city; battlefield trade placeholders are not city logistics.");
        List<Object> policies=new ArrayList<>(),flows=new ArrayList<>(),failures=new ArrayList<>();
        var types=init.trade.TRADE_TYPE.all;
        if(types.size()>16)return object("coverage","unavailable","scope","instantiated_city_trade",
            "policies",policies,"flows",flows,"truncated",true,"reason","Trade-type scan limit of 16 exceeded");
        int failed=0;boolean truncated=false;
        for(RESOURCE resource:RESOURCES.ALL()) {
            if(policies.size()+failed>=1000 || flows.size()+types.size()>4000){truncated=true;break;}
            try {
                var buyer=GAME.player().buyer(resource.tr());var seller=GAME.player().seller(resource.tr());
                List<Object> pending=new ArrayList<>();
                for(var type:types)pending.add(object("resource_id",resource.key,"trade_type_id",type.index,
                    "trade_type_name",type.name.toString(),
                    "inbound_reserved_units",buyer.toBeAdded().get(type),
                    "inbound_pending_placement_units",buyer.toBeStored().get(type),
                    "inbound_caravan_units",buyer.attempting(type),"inbound_total_units",buyer.incoming.get(type),
                    "outbound_reserved_units",seller.promised().get(type),
                    "outbound_caravan_units",seller.attempting(type),"outbound_total_units",seller.outbound.get(type)));
                Map<String,Object> policy=object("resource_id",resource.key,"reference_id","resource:"+resource.key,
                    "buy_price_cap_raw",buyer.priceCapsI.get(),"import_treasury_floor_credits",buyer.minMoney.get(),
                    "import_level_raw",buyer.limit.get(),"sell_price_floor_raw",seller.priceCapsI.get(),
                    "export_level_raw",seller.limit.get());
                policies.add(policy);flows.addAll(pending);
            } catch(RuntimeException error) {
                failed++;if(failures.size()<10)failures.add(object("resource_id",resource.key,"reason",error.getClass().getSimpleName()));
            }
        }
        return object("coverage","partial","scope","instantiated_city_trade","policies",policies,"flows",flows,
            "city_entry_closed",SETT.ENTRY().isClosed(),"resource_count_total",RESOURCES.ALL().size(),
            "resource_limit",1000,"flow_row_limit",4000,"trade_type_count",types.size(),"trade_type_scan_limit",16,
            "truncated",truncated,"failed_resources",failed,"failure_samples",failures,
            "reason","Resource tradables only. Aggregate staged bookkeeping for all mapped trade reasons, not a complete order list, caravan position/ETA or guaranteed ability to trade.");
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
            return object("stockpiles", rows,"stockpile_bookkeeping",stockpileBookkeeping(),"field_definitions",object(
                "owned",object("unit","resource units","scope","mixed_scene_logistics_and_player_trade_promises",
                    "definition","Game RESOURCE.owned(): reservable warehouse/hauler goods plus import/export/station goods and incoming station goods, minus player trade promises; not a warehouse-only count",
                    "source","init/resources/RESOURCE.java:537"),
                "stockpile_stored",object("unit","resource units","scope","instantiated_settlement_scene","source","SETT.ROOMS().STOCKPILE.tally().amount.total(resource)"),
                "stockpile_capacity",object("unit","resource units","scope","instantiated_settlement_scene","source","SETT.ROOMS().STOCKPILE.tally().space.total(resource)"),
                "stockpile_bookkeeping",object("scope","instantiated_city_stockpile_bookkeeping",
                    "source","settlement/room/infra/stockpile/StockpileTally.java:TallyData.total(int); public crates,amount,space,amountReserved,spaceReserved",
                    "relationships","resource_id joins stockpiles[].id and production/trade resource keys in this same observation; reference_id links installed resource help. Aggregate stockpile tallies only, not a room identity or UI selection.",
                    "assigned_crates","Resource-assigned crate count, not resource-item capacity or unassigned crates.",
                    "stored_raw","Stored resource items including reserved stored items; not free-to-use goods or all settlement inventory.",
                    "capacity_raw","Resource-specific assigned item capacity, not free capacity or physical floor area.",
                    "reserved_stored_raw","Reserved stored resource items; distinct from incoming capacity reservations.",
                    "reserved_incoming_raw","Reserved incoming capacity in resource items; not physically stored goods or guaranteed deliveries.",
                    "units","All quantity fields are resource items except assigned_crates (crates). Zero capacity is retained as zero; no fullness ratio/default/clamping is supplied. RESOURCE.owned has a broader mixed logistics/trade meaning.",
                    "limits","City-only. At most 1000 scanned resources/rows, ten failure samples. A failed resource emits no row; source diagnostics retain truncation/failures. Exact age and completion of reservations are unknown. No per-room/crate mapping, refresh, reservation action or cross-resource physical-fullness claim.")));
        }, "Owned resources, existing warehouse totals and bounded city stockpile reservation bookkeeping; excludes per-room/crate and in-transit breakdowns.");
        run(domains, "production", () -> {
            List<Object> rows = new ArrayList<>();
            for (RESOURCE r: RESOURCES.ALL()) {
                Map<String,Object> flow = new LinkedHashMap<>();
                for (RTYPE t: RTYPE.values()) flow.put(t.name(), object("in_current_day", GAME.player().res().in(t).get(r.tr()),
                    "out_current_day", GAME.player().res().out(t).get(r.tr())));
                rows.add(object("id", r.key, "flows", flow));
            }
            return object("resources", rows, "unit", "resource units", "period", "current history bucket (game day)",
                "room_data",roomProduction(),"field_definitions",object(
                    "resources",object("scope","campaign_player_or_faction","definition","Player resource ledger categories, not a per-room forecast."),
                    "room_data",object("scope","instantiated_settlement_scene","source","settlement/room/industry/module/IndustryResource.java; consumption/RoomConsumptionAbs.java; ROOM_PRODUCER_INSTANCE.java",
                        "definition","Bounded current-recipe input/output rows. room_id joins employment in the same observation; industry_id and recipe_index are runtime/load scoped. resource_id joins resource keys. Non-producer rooms are not a claim of zero production.",
                        "room_degradation_raw",object("source","settlement/room/main/RoomInstance.java:getDegrade; settlement/maintenance/ROOM_DEGRADER.java:get; MRoom.java:degrade",
                            "unit","Dimensionless stored normalized degradation; finite raw getter value, no clamping. Nonfinite values are null.",
                            "definition","One public getter read per included producer room, repeated on its recipe resource-flow rows. Do not sum this factor across flows. The shipped base decoder suppresses initial wear below its threshold: zero does not prove no wear or no maintenance need. Not remaining durability, present productivity, required maintenance resources or a complete production modifier.",
                            "age","Exact last wear/maintenance time is unavailable. This is a current read of a stored value, not a fresh wear calculation. No degrader handle, reporting, refresh or maintenance action is invoked. Non-producer rooms are outside this mapping; third-party overrides may change semantics."),
                        "units","Stored day/year fields are resource quantities. base_rate_raw is the configured recipe coefficient before modifiers, not realized per-worker or per-room output.",
                        "periods","day_accumulator_raw includes fractional carry across day rollovers. previous_day_units and year_units/previous_year_units are stored integer ledger buckets. The observer does not call updateRoom; paused or inactive rooms can retain an older bucket. Null nonfinite values stay unknown.")));
        }, "Player resource ledger plus bounded scene-local current recipe inputs/outputs and stored per-room quantities; not throughput forecasts or all production mechanics.");
        run(domains, "employment", () -> roomEmployment(),
            "Bounded room workforce counts/targets, stored employment factors and same-observation room key; not complete modifiers or worker histories.");
        run(domains, "research", () -> {
            List<Object> rows = new ArrayList<>(), requirements = new ArrayList<>(), costs = new ArrayList<>(), currencies = new ArrayList<>();
            game.faction.player.PTech playerTech=GAME.player().tech();
            for (TECH t: TECHS.ALL()) {
                int level=playerTech.level(t); boolean requirementsMet=true;
                for (TECH.TechRequirement requirement:t.requires()) {
                    int current=playerTech.level(requirement.tech); boolean met=current>=requirement.level;
                    requirementsMet &= met;
                    requirements.add(object("technology_id",t.key,"required_technology_id",requirement.tech.key,
                        "required_level",requirement.level,"current_level",current,"met",met));
                }
                rows.add(object("id",t.key,"name",t.name().toString(),"reference_id","technology:"+t.key,
                    "level",level,"max_level",t.levelMax,"technology_requirements_met",requirementsMet));
                for (init.tech.TechCost cost:t.costs) costs.add(object("technology_id",t.key,"currency_id",cost.cu.bo.key,
                    "base_amount",cost.amount,"allocated_for_current_level",playerTech.costTotal(cost,t),
                    "next_level_cost",level<t.levelMax?playerTech.costLevelNext(cost.amount,t):null));
            }
            for(game.faction.player.PTech.TechCurr currency:playerTech.currs()) {
                double penalty=currency.penalty();
                currencies.add(object("id",currency.cu.bo.key,"name",currency.cu.bo.name.toString(),
                    "reference_id","research_currency:"+currency.cu.bo.key,
                    "total",currency.total(),"allocated",currency.allocated(),"frozen",currency.frozen(),
                    "available",currency.available(),"penalty_raw",Double.isFinite(penalty)?penalty:null));
            }
            return object("technologies",rows,"requirements",requirements,"costs",costs,"currencies",currencies,
                "field_definitions",object(
                    "requirements",object("definition","Expanded prerequisite closure returned by TECH.requires(), not only direct tree edges; technology_requirements_met checks these levels only and does not establish other unlock conditions or affordability.",
                        "source","init/tech/TECHS.java; init/tech/TECH.java"),
                    "costs",object("unit","points of the identified currency", "definition","Base cost and public PTech cost getters. next_level_cost is null at maximum level and excludes missing prerequisites; allocated_for_current_level is the total allocation for this technology, not currency availability.",
                        "source","game/faction/player/PTech.java; init/tech/TechCost.java"),
                    "currencies",object("unit","points of each identified currency", "definition","Current public TechCurr values. available = total - frozen - allocated, and can be negative; frozen is rounded upward by the game. penalty_raw is the stored game penalty factor, not a forecast or recalculated per-technology penalty.",
                        "source","game/faction/player/PTech.java:TechCurr")));
        }, "Technology levels, expanded prerequisite levels, currency allocation and next-level cost getters; not a full unlock decision, effect schema, research forecast or history.");
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
            return object("resources",rows,"period","current game-day bucket","unit","resource units",
                "settlement_pipeline",tradePipeline(),"field_definitions",object(
                    "resources",object("scope","campaign_player_or_faction","definition","Recorded current-day import/export ledger totals; not the staged settlement pipeline."),
                    "settlement_pipeline",object("scope","instantiated_city_trade","unit","resource units unless otherwise specified",
                        "source","settlement/trade/PBuyer.java; PSeller.java; PBuyerRes.java; PSellerRes.java; Player.buyer/seller -> SETT.TRADE()",
                        "relationships","resource_id joins resources.stockpiles[].id in the same observation. trade_type_id is the installed TRADE_TYPE.index; names are display labels, not permanent IDs.",
                        "stages","inbound_reserved_units reads toBeAdded; inbound_pending_placement_units reads toBeStored; inbound_caravan_units reads attempting. inbound_total_units is their public incoming sum. outbound_reserved_units reads promised; outbound_caravan_units reads attempting; outbound_total_units is their public outbound sum. All trade reasons are retained, including tax, trade, spoils and diplomacy; these are not all market purchases.",
                        "limits","At most 1000 resource tradables, 4000 stage rows and 16 trade reasons; a resource batch is never split. Failed resources emit no partial policy/stage batch. Missing or unavailable rows are not zero. No trade updater is invoked."),
                    "trade_policy",object("scope","instantiated_city_trade","source","PBuyer.priceCapsI/minMoney/limit; PSeller.priceCapsI/limit (public IntImp.get)",
                        "prices","Configured per-unit buy cap/sell floor in game credits, not a current executable quote, tariff-inclusive price or profit forecast. import_treasury_floor_credits is the configured buyer floor.",
                        "levels","import_level_raw/export_level_raw are resource configuration integers (0..100 in the shipped resource adapters). Import 100 has special fill-capacity behavior; do not interpret it as a simple warehouse-only target. These settings alone do not prove an order can execute.")));

        }, "Campaign current-day resource ledgers plus bounded city resource trade stages and configured limits; no full order list, executable quote or ETA.");
        run(domains, "diplomacy", () -> {
            List<Object> rows=new ArrayList<>();
            for(game.faction.Faction f: game.faction.FACTIONS.active()) {
                if(f==GAME.player()) continue;
                game.faction.diplomacy.DipStance stance=game.faction.diplomacy.DIP.get(GAME.player(),f);
                rows.add(object("id",f.index(),"name",f.name.toString(),"stance_id",stance.key(),"stance",stance.name.toString()));
            }
            return object("factions",rows);
        }, "Current diplomatic stances; not treaties, relationship factors or hidden intentions.");
        run(domains, "world", StateCollector::worldData,
            "Bounded campaign region identity, ownership, population and stored resource-output accrual/schedules; not a complete economy, settlement census, growth/shipping forecast or UI selection.");
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
            "weather",WeatherObservation.collect(),"on_demand_tool","query_live_tiles","tile_fields",Arrays.asList("terrain","floor","room","minerals","path","ground_moisture")),
            "Scene dimensions, completed instantiated-city stored weather and supported on-demand tiles. Weather is not regional weather, physical units, crop yield or forecast; tile rows require bounded queries.");
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
            if(group.getKey().equals("services")) {
                data.put("room_data",roomServices());
                data.put("access_policy",servicePolicies());
                data.put("field_definitions",object("room_data",object(
                    "scope","instantiated_settlement_scene","source","settlement/room/service/module/ROOM_SERVICER.java; RoomServiceInstance.java",
                    "room_id","Public RoomInstance.index(), joins employment.room_id in the same observation; not a permanent identity or selected room.",
                    "total_slots_raw","Stored RoomServiceInstance.total(): configured count of service points for this instance, with room-specific meaning; not daily throughput or people capacity.",
                    "available_slots_raw","Stored RoomServiceInstance.available(): reported reservable service-point count; not proof a particular citizen can reach or use it.",
                    "reserved_slots_raw","Stored RoomServiceInstance.reserved(): reported reserved service-point count; total minus available need not equal reserved.",
                    "active","Public room activation flag. Inactive rooms can still retain stored counters; no refresh is performed.",
                    "missing","Only instances implementing public ROOM_SERVICER are included. Other rooms, failures and truncation are not zero counts."),
                    "access_policy",object("scope","instantiated_city_service_configuration",
                        "source","settlement/room/service/module/RoomServiceAccess.java; settlement/stats/service/StatServiceImp.java; init/type/HCLASS_RACE.java",
                        "allowed_by_configured_rule","Public permission().is(HCLASS_RACE.clP(race,class)): configured cohort flag only, not effective individual eligibility. Nobles/tourists and child-parent rules can override or add conditions.",
                        "relationships","service_id joins service_types in this observation; blueprint_id joins room_data/rooms.blueprint_id, including one-to-many instances. A registered type need not have a built room. Race/class keys join population cohorts; do not join by translated names.",
                        "limits","At most 256 service types, 10000 rule rows and 64 races/classes. Each service type is emitted with its entire cohort batch, or omitted on failure/cap. Missing rules are not denial. No aggregate null-race/class settings are exported.")));
            }
            if(group.getKey().equals("housing"))data.put("home_records",HousingObservation.collect(10000,1000));
            if(group.getKey().equals("military"))data.put("scene_armies",Arrays.asList(sceneArmy("player",GAME.ARMIES().player()),sceneArmy("enemy",GAME.ARMIES().enemy())));
            return data;
        }, group.getKey().equals("military")?"Public battle aggregates and scene division rows; not every campaign army, private order state or combat history":group.getKey().equals("housing")?"Public HOME statistics and bounded source-verified home records/rosters/cohort ledgers; not physical presence, effective vacancy, permanent identity or complete housing mechanics.":group.getKey().equals("services")?"Public service aggregates, bounded per-room stored service-point counters and city cohort permission configuration; not demand, daily capacity, effective individual access or complete service mechanics.":"Public aggregate statistics only; no causal/historical completeness is claimed.");
        Set<String> sceneDomains=Set.of("population","resources","employment","services","housing","health","law","happiness","military","map","entities");
        for(String key:DOMAINS) {
            Map<String,Object> record=(Map<String,Object>)domains.get(key);
            String scope=sceneDomains.contains(key)?"instantiated_settlement_scene":
                Set.of("production","trade","research","diplomacy").contains(key)?"campaign_player_or_faction":"game_or_world";
            if(key.equals("resources"))scope="mixed_scene_logistics_and_player_trade_promises";
            if(key.equals("production"))scope="mixed_scene_production_and_campaign_ledger";
            if(key.equals("trade"))scope="mixed_city_trade_pipeline_and_campaign_ledger";
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
