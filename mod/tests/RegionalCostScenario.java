import game.GAME;
import init.resources.*;
import init.trade.TR;
import world.WORLD;
import world.region.RD;
import world.map.regions.Region;
import snake2d.CORE;
import syx.assistant.RegionalReadRequest;
import syx.assistant.JsonWriter;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** TEST ONLY: unchanged copied campaign; exact production request collector timings. */
public final class RegionalCostScenario {
    @SuppressWarnings("unchecked")
    public static void install(Path directory) {
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();
        List<Region> regions=new ArrayList<>();for(Region r:WORLD.REGIONS().active())if(regions.size()<100)regions.add(r);
        List<RESOURCE> resources=new ArrayList<>();for(RESOURCE r:RESOURCES.ALL())resources.add(r);
        if(regions.size()!=100 || resources.size()>100 || regions.size()*resources.size()<=4096)
            throw new IllegalStateException("Requires a >4096-cell finite copied campaign");
        // Independent public-getter expectations, never write game counters or faction state.
        List<Object> all=new ArrayList<>();
        for(Region region:regions)for(RESOURCE resource:resources) {
            var output=RD.OUTPUT().get(TR.get(resource));var faction=region.faction();
            int amount=output.yearlyAccumilation.get(region);
            if(amount<0 || amount==Integer.MAX_VALUE || faction!=null && faction.index()==Integer.MAX_VALUE)
                throw new IllegalStateException("Fixture requires nonnegative counters and absent max-int amount/faction");
            Map<String,Object> row=new LinkedHashMap<>();row.put("region_id",region.index());row.put("resource_id",resource.key);
            row.put("accrued_output_raw",amount);row.put("days_until_configured_output",output.daysUntilDailydelivery());
            row.put("reference_id","resource:"+resource.key);row.put("faction_id",faction==null?null:faction.index());all.add(row);
        }
        List<Integer> ids=new ArrayList<>();for(Region r:regions)ids.add(r.index());
        List<String> keys=new ArrayList<>(),encodedKeys=new ArrayList<>();
        for(RESOURCE r:resources){keys.add(r.key);encodedKeys.add(Base64.getUrlEncoder().withoutPadding().encodeToString(r.key.getBytes(StandardCharsets.UTF_8)));}
        String session=UUID.randomUUID().toString();String[] names={"single_cell","full_row_page","empty_amount_scan_cap","empty_faction_scan_cap"};
        List<Object> samples=new ArrayList<>();int[] sample={0};long began=System.nanoTime();long[] last={0};boolean[] written={false};
        GAME.addAfterUpdate(()->{
            try {
                if(Files.exists(directory.resolve("verifier.done"))) {CORE.annihilate();return;}
                long now=System.nanoTime();if(now-began>150_000_000_000L)throw new IllegalStateException("Cost verifier timed out");
                if(written[0] || now-began<10_000_000_000L || now-last[0]<250_000_000L)return;
                last[0]=now;int kind=sample[0]%4;boolean single=kind==0;
                String wire="protocol=1\nrequest_id="+UUID.randomUUID()+"\nsession="+session+"\nexpires="+(System.currentTimeMillis()+8000)+
                    "\nregions="+(single?ids.get(0):String.join(",",ids.stream().map(Object::toString).toList()))+
                    "\nresources="+(single?encodedKeys.get(0):String.join(",",encodedKeys))+
                    "\nfields=accrued_output_raw,days_until_configured_output,reference_id,faction_id\ncursor=0\nscan_limit=4096\nlimit=100\nminimum="+
                    (kind==2?Integer.MAX_VALUE:"")+"\nmaximum=\nfaction="+(kind==3?Integer.MAX_VALUE:"")+"\n";
                // Production parses off-thread. Exclude parsing/validation/file I/O from collector timing.
                RegionalReadRequest request=RegionalReadRequest.parse(wire);
                long start=System.nanoTime();Map<String,Object> result=request.collect(session);long collected=System.nanoTime();
                byte[] bytes=JsonWriter.encode(result).getBytes(StandardCharsets.UTF_8);long encoded=System.nanoTime();
                if(!Boolean.TRUE.equals(result.get("available")))throw new IllegalStateException("Unavailable cost request: "+result.get("reason"));
                Map<String,Object> data=(Map<String,Object>)result.get("data");
                int scanned=single?1:kind==1?100:4096;Integer next=single?null:scanned;
                List<Object> expected=kind>=2?List.of():all.subList(0,scanned);
                if(!expected.equals(data.get("rows")) || !Integer.valueOf(scanned).equals(data.get("scanned_cells")) ||
                    !Integer.valueOf(0).equals(data.get("cell_errors")) || !Objects.equals(next,data.get("next_cursor")) || bytes.length>65536)
                    throw new IllegalStateException("Independent cost-row/cursor/error/byte parity failed");
                samples.add(Map.of("case",names[kind],"sample",sample[0]/4,"collector_ns",collected-start,
                    "encoding_utf8_ns",encoded-collected,"response_bytes",bytes.length,"scanned_cells",scanned,"returned_rows",expected.size()));
                if(++sample[0]==128) {
                    Map<String,Object> report=new LinkedHashMap<>();report.put("samples",samples);report.put("region_ids",ids);report.put("resource_ids",keys);
                    report.put("active_regions",WORLD.REGIONS().active().size());report.put("loaded_resources",resources.size());
                    report.put("expected_page_rows",all.subList(0,100));report.put("java_version",System.getProperty("java.version"));
                    report.put("all_sample_getter_parity",true);report.put("game_state_writes","Only paused speed and settlement view setup; no data/counter writes.");
                    Files.writeString(directory.resolve("regional-cost-fixture.json"),JsonWriter.encode(report));written[0]=true;
                }
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
