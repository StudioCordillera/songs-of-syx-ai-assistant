import game.GAME;
import game.time.TIME;
import init.resources.*;
import init.trade.TR;
import world.WORLD;
import world.map.regions.Region;
import world.region.RD;
import world.region.RDOutputs.RDResource;
import snake2d.CORE;
import syx.assistant.JsonWriter;
import java.nio.file.*;
import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.util.*;

/** TEST ONLY: bounded stored reads plus immediately restored public counter writes in a copied game. */
public final class RegionalOutputScenario {
    static int[] read(List<Region> regions,List<RDResource> outputs) {
        int[] values=new int[regions.size()*outputs.size()];int i=0;
        for(Region region:regions)for(RDResource output:outputs)values[i++]=output.yearlyAccumilation.get(region);
        return values;
    }
    static String digest(int[] values)throws Exception {
        ByteBuffer bytes=ByteBuffer.allocate(values.length*4);for(int value:values)bytes.putInt(value);
        byte[] hash=MessageDigest.getInstance("SHA-256").digest(bytes.array());
        StringBuilder text=new StringBuilder();for(byte b:hash)text.append(String.format("%02x",b));return text.toString();
    }
    public static void install(Path directory) {
        if(!WORLD.GEN().isDone)throw new IllegalStateException("Requires completed copied world");
        GAME.SPEED.speedSet(0);view.main.VIEW.s().activate();
        List<Region> regions=new ArrayList<>();List<RDResource> outputs=new ArrayList<>();List<String> resourceIds=new ArrayList<>();
        for(var region:WORLD.REGIONS().active())regions.add(region);
        if(regions.isEmpty() || regions.size()>1023 || RESOURCES.ALL().size()>1000 || (long)regions.size()*RESOURCES.ALL().size()>10000)
            throw new IllegalStateException("Native candidate scan exceeds explicit bounds or is empty");
        for(RESOURCE resource:RESOURCES.ALL()) {
            var tradable=TR.get(resource);var output=RD.OUTPUT().get(tradable);
            if(output.res!=tradable || !output.res.key().equals(tradable.key()))throw new IllegalStateException("Resource/tradable/output mapping mismatch");
            outputs.add(output);resourceIds.add(resource.key);
        }
        final long began=System.nanoTime();long[] last={0};int[] sample={0};int[][] baseline={null};
        boolean[] complete={false};List<Object> timings=new ArrayList<>();
        GAME.addAfterUpdate(()->{
            try {
                if(Files.exists(directory.resolve("verifier.done"))){CORE.annihilate();return;}
                long now=System.nanoTime();
                if(now-began>100_000_000_000L)throw new IllegalStateException("Regional candidate verifier timed out");
                if(complete[0] || now-began<8_000_000_000L || now-last[0]<250_000_000L)return;
                last[0]=now;
                if(baseline[0]==null) {
                    baseline[0]=read(regions,outputs);Region target=regions.get(0);RDResource output=outputs.get(0);
                    int original=output.yearlyAccumilation.get(target);
                    try {
                        for(int value:new int[]{0,37,Integer.MAX_VALUE}) {
                            output.yearlyAccumilation.set(target,value);
                            int[] changed=read(regions,outputs);
                            if(changed[0]!=value)throw new IllegalStateException("Controlled public setter/getter mismatch");
                            for(int i=1;i<changed.length;i++)if(changed[i]!=baseline[0][i])throw new IllegalStateException("Unrelated counter changed");
                        }
                    } finally {output.yearlyAccumilation.set(target,original);}
                    if(!Arrays.equals(baseline[0],read(regions,outputs)))throw new IllegalStateException("Controlled counter restoration failed");
                }
                long start=System.nanoTime();int[] values=read(regions,outputs);long end=System.nanoTime();
                if(!Arrays.equals(values,baseline[0]))throw new IllegalStateException("Paused world counters changed during candidate reads");
                timings.add(Map.of("sample",sample[0],"read_and_int_array_ns",end-start,"cells",values.length));sample[0]++;
                if(sample[0]==32) {
                    int positive=0,zero=0,negative=0;for(int value:values)if(value>0)positive++;else if(value==0)zero++;else negative++;
                    if(negative!=0)throw new IllegalStateException("Candidate counter outside reviewed nonnegative range");
                    int yearDays=(int)TIME.years().bitConversion(TIME.days());int day=TIME.days().bitsSinceStart()%yearDays;
                    int offsets=0;
                    for(int i=0;i<outputs.size();i++) {
                        RESOURCE resource=RESOURCES.ALL().get(i);int target=0;
                        for(Growable growable:RESOURCES.growable().all())if(growable.resource==resource){target=(int)(growable.seasonalOffset*yearDays);break;}
                        int expected=target>=day?target-day:yearDays-day+target;
                        if(outputs.get(i).daysUntilDailydelivery()!=expected)throw new IllegalStateException("Configured day-offset mismatch");
                        offsets++;
                    }
                    List<Integer> regionIds=new ArrayList<>();for(Region region:regions)regionIds.add(region.index());
                    Map<String,Object> fixture=new LinkedHashMap<>();
                    fixture.put("passed",true);fixture.put("region_ids",regionIds);fixture.put("resource_ids",resourceIds);
                    fixture.put("shape",Map.of("regions",regions.size(),"resources",outputs.size(),"counter_cells",values.length,
                        "natural_positive_cells",positive,"natural_zero_cells",zero,"negative_cells",negative));
                    fixture.put("configured_day_offset_checks",offsets);fixture.put("controlled_values",List.of(0,37,Integer.MAX_VALUE));
                    fixture.put("unrelated_cells_unchanged_during_controls",true);fixture.put("controlled_counter_restored",true);
                    fixture.put("repeated_matrix_unchanged",true);fixture.put("matrix_sha256",digest(values));fixture.put("samples",timings);
                    fixture.put("limits",List.of("Paused finite copied world; candidate only, no new production observation or MCP counter parity.",
                        "Controlled public setter calls affect one disposable counter only and restore it in the same callback; no saves.",
                        "No shipper, boost, cache refresh, ownership transfer or actual seasonal delivery/arrival action is invoked.",
                        "Read timings include array allocation and getter traversal only, not snapshot collection/encoding/MCP/FPS or representative large-world acceptance."));
                    Files.writeString(directory.resolve("regional-output-reader-fixture.json"),JsonWriter.encode(fixture));
                    complete[0]=true;System.err.println("REGIONAL OUTPUT CANDIDATE: 32 bounded matrices and restored controls ready");
                }
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
