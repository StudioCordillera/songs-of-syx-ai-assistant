import game.GAME;
import settlement.main.SETT;
import snake2d.CORE;
import snake2d.util.map.MAP_DOUBLE;
import syx.assistant.JsonWriter;
import view.main.VIEW;
import java.nio.file.*;
import java.util.*;
import static syx.assistant.StateCollector.object;

/** TEST ONLY: public stored readers in an unchanged paused copied city; no moisture writes. */
public final class GroundMoistureScenario {
    public static void install(Path directory) {
        VIEW.s().activate();GAME.SPEED.speedSet(0);
        if(!SETT.exists() || SETT.TWIDTH<64 || SETT.THEIGHT<64)throw new IllegalStateException("Requires instantiated copied map >=64x64");
        MAP_DOUBLE base=SETT.GROUND().MOISTURE_BASE,current=SETT.GROUND().MOISTURE_CURRENT;
        int[][] coordinates=new int[4096][2];
        for(int i=0;i<4096;i++){coordinates[i][0]=(i%64)*(SETT.TWIDTH-1)/63;coordinates[i][1]=(i/64)*(SETT.THEIGHT-1)/63;}
        double[][] first=new double[4096][2];double[][] values=new double[4096][2];
        List<Object> samples=new ArrayList<>();long began=System.nanoTime();long[] last={0};boolean[] written={false};
        GAME.addAfterUpdate(()->{
            try {
                if(Files.exists(directory.resolve("verifier.done"))) {
                    if(!written[0])throw new IllegalStateException("Verifier completed before candidate samples");
                    Files.writeString(directory.resolve("ground-moisture-clean-exit.json"),JsonWriter.encode(object("passed",true,"samples",64)));
                    CORE.annihilate();return;
                }
                long now=System.nanoTime();if(now-began>150_000_000_000L)throw new IllegalStateException("Moisture verifier timed out");
                if(written[0] || now-began<3_000_000_000L || now-last[0]<100_000_000L)return;
                last[0]=now;
                // Arrays allocated before timing. Only two coordinate getters plus loop/stores are timed.
                long start=System.nanoTime();
                for(int i=0;i<4096;i++){int x=coordinates[i][0],y=coordinates[i][1];values[i][0]=base.get(x,y);values[i][1]=current.get(x,y);}
                long finished=System.nanoTime();
                int different=0,changed=0;Set<Double> distinctBase=new HashSet<>(),distinctCurrent=new HashSet<>();
                double minBase=1,maxBase=0,minCurrent=1,maxCurrent=0;
                for(int i=0;i<4096;i++) {
                    int x=coordinates[i][0],y=coordinates[i][1],tile=x+y*SETT.TWIDTH;double b=values[i][0],c=values[i][1];
                    if(!Double.isFinite(b) || !Double.isFinite(c) || b<0 || b>1 || c<0 || c>1 ||
                        Math.abs(b*15-Math.rint(b*15))>1e-10 || Math.abs(c*15-Math.rint(c*15))>1e-10 ||
                        b!=base.get(tile) || c!=current.get(tile))throw new IllegalStateException("Coordinate/linear/normalization mismatch");
                    if(samples.isEmpty()){first[i][0]=b;first[i][1]=c;}
                    if(b!=c)different++;if(b!=first[i][0] || c!=first[i][1])changed++;
                    distinctBase.add(b);distinctCurrent.add(c);minBase=Math.min(minBase,b);maxBase=Math.max(maxBase,b);minCurrent=Math.min(minCurrent,c);maxCurrent=Math.max(maxCurrent,c);
                }
                samples.add(object("sample",samples.size(),"reader_loop_ns",finished-start,"tile_count",4096,"public_getter_calls_in_timed_loop",8192,
                    "coordinate_linear_comparisons",8192,"different_base_current_tiles",different,"changed_from_first_tiles",changed,
                    "distinct_base_values",distinctBase.size(),"distinct_current_values",distinctCurrent.size(),
                    "base_min",minBase,"base_max",maxBase,"current_min",minCurrent,"current_max",maxCurrent));
                if(samples.size()==64) {
                    List<Object> points=new ArrayList<>();
                    for(int i=0;i<4096;i++)points.add(Arrays.asList(coordinates[i][0],coordinates[i][1],first[i][0],first[i][1]));
                    List<Object> invalid=new ArrayList<>();
                    for(int[] xy:new int[][]{{-1,0},{0,-1},{SETT.TWIDTH,0},{0,SETT.THEIGHT}}) {
                        if(SETT.IN_BOUNDS(xy[0],xy[1]) || base.get(xy[0],xy[1])!=0 || current.get(xy[0],xy[1])!=0)throw new IllegalStateException("Out-of-bounds default changed");
                        invalid.add(Arrays.asList(xy[0],xy[1]));
                    }
                    List<Object> anchors=new ArrayList<>();
                    for(int i:new int[]{0,63,4032,4095}){int x=coordinates[i][0],y=coordinates[i][1];anchors.add(object("tile_x",x,"tile_y",y,"terrain_id",SETT.TERRAIN().get(x,y).key()));}
                    Files.writeString(directory.resolve("ground-moisture-fixture.json"),JsonWriter.encode(object("passed",true,"width",SETT.TWIDTH,"height",SETT.THEIGHT,
                        "sample_points",points,"samples",samples,"out_of_bounds_zero_points",invalid,"anchors",anchors,"scene",syx.assistant.UiContextCollector.scene())));
                    written[0]=true;
                }
            }catch(Exception error){
                System.err.println("SMOKE_FIXTURE_FAILURE: "+error);
                try{Files.writeString(directory.resolve("ground-moisture-fixture-failure.json"),error.getClass().getSimpleName());}catch(Exception ignored){}
                CORE.annihilate(error);
            }
        });
    }
}
