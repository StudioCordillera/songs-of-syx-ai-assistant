import game.GAME;
import init.resources.*;
import init.trade.TR;
import world.WORLD;
import world.region.RD;
import world.map.regions.Region;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import syx.assistant.RegionalReadRequest;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;

/** TEST ONLY: held/restored copied counter, public getters, exact production capture cost. */
public final class RegionalCaptureScenario {
    @SuppressWarnings("unchecked")
    public static void install(Path directory,Path save) {
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();
        List<Region> regions=new ArrayList<>();for(Region r:WORLD.REGIONS().active())if(regions.size()<100)regions.add(r);
        List<RESOURCE> resources=new ArrayList<>();for(RESOURCE r:RESOURCES.ALL())resources.add(r);
        if(regions.size()!=100 || resources.size()>100 || regions.size()*resources.size()<=4096)throw new IllegalStateException("Requires >4096 finite cells");
        int prefix=2000/resources.size();Region target=regions.get(99);RESOURCE resource=resources.get(resources.size()-1);
        var counter=RD.OUTPUT().get(TR.get(resource)).yearlyAccumilation;int original=counter.get(target);
        List<Integer> ids=new ArrayList<>();for(Region r:regions)ids.add(r.index());
        List<String> keys=new ArrayList<>(),encoded=new ArrayList<>();for(RESOURCE r:resources){keys.add(r.key);encoded.add(Base64.getUrlEncoder().withoutPadding().encodeToString(r.key.getBytes(StandardCharsets.UTF_8)));}
        List<Object> all=new ArrayList<>(),positive=new ArrayList<>(),timings=new ArrayList<>();
        String session=UUID.randomUUID().toString();long began=System.nanoTime();long[] last={0};int[] sample={0};boolean[] held={false},written={false},restored={false},started={false};
        GAME.addAfterUpdate(()->{
            try {
                if(started[0])return;
                if(Files.exists(directory.resolve("regional-capture.done"))) {
                    counter.set(target,original);if(counter.get(target)!=original)throw new IllegalStateException("Counter restore failed");
                    started[0]=true;SceneScenario.install(directory,save);return;
                }
                if(Files.exists(directory.resolve("regional-capture-change.request")) && !restored[0]) {
                    counter.set(target,original);if(counter.get(target)!=original)throw new IllegalStateException("Counter restore failed");
                    view.main.VIEW.world().activate();restored[0]=true;
                    Files.writeString(directory.resolve("regional-capture-restored.json"),JsonWriter.encode(Map.of("passed",true,"restored_value",original,"tick",GAME.updateI())));
                }
                long now=System.nanoTime();if(now-began>180_000_000_000L)throw new IllegalStateException("Capture verifier timed out");
                if(written[0] || now-began<5_000_000_000L || now-last[0]<250_000_000L)return;
                last[0]=now;
                if(!held[0]) {
                    counter.set(target,Integer.MAX_VALUE);held[0]=true;
                    for(Region region:regions)for(RESOURCE r:resources) {
                        var output=RD.OUTPUT().get(TR.get(r));var owner=region.faction();
                        Map<String,Object> row=new LinkedHashMap<>();row.put("region_id",region.index());row.put("resource_id",r.key);
                        row.put("accrued_output_raw",output.yearlyAccumilation.get(region));row.put("days_until_configured_output",output.daysUntilDailydelivery());
                        row.put("reference_id","resource:"+r.key);row.put("faction_id",owner==null?null:owner.index());all.add(row);
                        if(((Number)row.get("accrued_output_raw")).intValue()>0)positive.add(row);
                    }
                    if(positive.size()<=100 || positive.size()>2000)throw new IllegalStateException("Requires 101..2000 positive cells");
                }
                boolean filtered=sample[0]%2==0;
                String wire="protocol=2\nrequest_id="+UUID.randomUUID()+"\nsession="+session+"\nexpires="+(System.currentTimeMillis()+8000)+
                    "\nregions="+String.join(",",ids.subList(0,filtered?100:prefix).stream().map(Object::toString).toList())+
                    "\nresources="+String.join(",",encoded)+"\nfields=accrued_output_raw,days_until_configured_output,reference_id,faction_id\ncursor=0\nscan_limit=10000\nlimit=2000\nminimum="+(filtered?"1":"")+"\nmaximum=\nfaction=\n";
                RegionalReadRequest request=RegionalReadRequest.parse(wire);
                long start=System.nanoTime();Map<String,Object> response=request.collect(session);long collected=System.nanoTime();
                byte[] bytes=JsonWriter.encode(response).getBytes(StandardCharsets.UTF_8);long serialized=System.nanoTime();
                Map<String,Object> data=(Map<String,Object>)response.get("data");List<Object> expected=filtered?positive:all.subList(0,prefix*resources.size());
                int scanned=(filtered?100:prefix)*resources.size();
                if(!Boolean.TRUE.equals(response.get("available")) || !"regional_capture".equals(response.get("read_mode")) ||
                    data==null || !expected.equals(data.get("rows")) || !Integer.valueOf(scanned).equals(data.get("scanned_cells")) ||
                    !Integer.valueOf(0).equals(data.get("cell_errors")) || data.get("next_cursor")!=null || bytes.length>2*1024*1024)
                    throw new IllegalStateException("Native complete-capture parity failed");
                timings.add(Map.of("case",filtered?"filtered_matrix":"near_row_bound","sample",sample[0]/2,"collector_ns",collected-start,
                    "encoding_utf8_ns",serialized-collected,"response_bytes",bytes.length,"rows",expected.size(),"scanned_cells",scanned));
                if(++sample[0]==64) {
                    Map<String,Object> fixture=new LinkedHashMap<>();fixture.put("region_ids",ids);fixture.put("resource_ids",keys);fixture.put("rows",all);
                    fixture.put("prefix_regions",prefix);fixture.put("target_region",target.index());fixture.put("target_resource",resource.key);
                    fixture.put("original_value",original);fixture.put("timings",timings);fixture.put("started_at",Instant.now().toString());
                    Files.writeString(directory.resolve("regional-capture-fixture.json"),JsonWriter.encode(fixture));written[0]=true;
                }
            }catch(Exception failure){counter.set(target,original);CORE.annihilate(failure);}
        });
    }
}
