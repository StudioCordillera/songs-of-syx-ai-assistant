import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import game.GAME;
import snake2d.CORE;
import syx.assistant.StateCollector;
import syx.assistant.JsonWriter;

/** TEST ONLY: time the exact exported collector; private observations never replace bridge state. */
public final class CollectionCostScenario {
    @SuppressWarnings("unchecked")
    public static void install(Path directory) {
        GAME.SPEED.speedSet(0);
        long began=System.nanoTime();long[] last={0};int[] sample={0};boolean[] written={false};
        String session=UUID.randomUUID().toString();List<Object> timings=new ArrayList<>();
        GAME.addAfterUpdate(()->{
            try {
                long now=System.nanoTime();
                if(now-began>10_000_000_000L && !written[0] && now-last[0]>=250_000_000L) {
                    last[0]=now;
                    // Only the mod's detached help cache is cleared; no game-state setter.
                    if(sample[0]==0)StateCollector.clearReferenceCache();
                    long start=System.nanoTime();Map<String,Object> observation=StateCollector.collect(session,sample[0]+1);
                    long collected=System.nanoTime();byte[] encoded=JsonWriter.encode(observation).getBytes(StandardCharsets.UTF_8);
                    long serialized=System.nanoTime();
                    Map<String,Object> scene=(Map<String,Object>)observation.get("scene");
                    if(!"city".equals(scene.get("settlement_scene_kind")))throw new IllegalStateException("Requires instantiated copied city");
                    Map<String,Object> domains=(Map<String,Object>)observation.get("domains");
                    for(Object value:domains.values())if(!"partial".equals(((Map<String,Object>)value).get("coverage")))throw new IllegalStateException("Unavailable domain during collection profile");
                    Map<String,Object> services=(Map<String,Object>)((Map<String,Object>)domains.get("services")).get("data");
                    Map<String,Object> rooms=(Map<String,Object>)services.get("room_data");
                    Map<String,Object> policy=(Map<String,Object>)services.get("access_policy");
                    if(Boolean.TRUE.equals(rooms.get("truncated")) || Boolean.TRUE.equals(policy.get("truncated")) ||
                       ((Number)rooms.get("failed_rooms")).intValue()!=0 || ((Number)policy.get("failed_service_types")).intValue()!=0)
                        throw new IllegalStateException("Service profile contains truncated/failed reads");
                    Map<String,Object> resources=(Map<String,Object>)((Map<String,Object>)domains.get("resources")).get("data");
                    Map<String,Object> stockpile=(Map<String,Object>)resources.get("stockpile_bookkeeping");
                    if(!"partial".equals(stockpile.get("coverage")) || Boolean.TRUE.equals(stockpile.get("truncated")) ||
                       ((Number)stockpile.get("failed_resources")).intValue()!=0 ||
                       ((Number)stockpile.get("scanned_resources")).intValue()!=((Number)stockpile.get("resource_count_total")).intValue())
                        throw new IllegalStateException("Stockpile profile contains unavailable/truncated/failed reads");
                    timings.add(Map.of("cache",sample[0]==0?"cold_mod_help_cache":"warm_mod_help_cache",
                        "collection_ns",collected-start,"encoding_utf8_ns",serialized-collected,"combined_ns",serialized-start,
                        "snapshot_bytes",encoded.length));
                    sample[0]++;
                    if(sample[0]==32) {
                        // Retain the real timestamp. This separate profiling envelope has its own
                        // session and is offline evidence, never the active SCRIPT's snapshot.
                        Files.write(directory.resolve("collection-observation.json"),encoded);
                        Map<String,Object> production=(Map<String,Object>)((Map<String,Object>)domains.get("production")).get("data");
                        Map<String,Object> productionRooms=(Map<String,Object>)production.get("room_data");
                        Map<String,Object> world=(Map<String,Object>)((Map<String,Object>)domains.get("world")).get("data");
                        Map<String,Object> entities=(Map<String,Object>)((Map<String,Object>)domains.get("entities")).get("data");
                        Files.writeString(directory.resolve("collection-cost-fixture.json"),JsonWriter.encode(Map.of(
                            "passed",true,"samples",timings,"domain_count",domains.size(),
                            "reference_count",((List<?>)observation.get("references")).size(),
                            "shape",Map.of("scanned_rooms",rooms.get("scanned_rooms"),"service_room_rows",((List<?>)rooms.get("rooms")).size(),
                                "service_policy_rows",((List<?>)policy.get("cohort_rules")).size(),"production_flow_rows",((List<?>)productionRooms.get("flows")).size(),
                                "regional_rows",((List<?>)world.get("regions")).size(),"entity_prefix_rows",((List<?>)entities.get("items")).size(),
                                "stockpile_resource_rows",((List<?>)stockpile.get("rows")).size(),"stockpile_scanned_resources",stockpile.get("scanned_resources")),
                            "java_version",System.getProperty("java.version"),"os",System.getProperty("os.name"),
                            "limits",List.of("Paused copied city only; no larger-city or worst-case/cap claim.",
                                "Cold means this mod's reference cache only, not cold game/JVM/filesystem caches.",
                                "Game-thread collection and JSON/UTF-8 encoding measured separately; disk I/O, MCP, model and game loading excluded.",
                                "Profiling envelope is a separate real observation used offline, never the active bridge session."))));
                        written[0]=true;System.err.println("COLLECTION COST TEST: 1 cold and 31 warm samples ready");
                    }
                }
                if(Files.exists(directory.resolve("verifier.done")) || System.nanoTime()-began>110_000_000_000L)CORE.annihilate();
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
