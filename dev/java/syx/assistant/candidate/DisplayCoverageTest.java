package syx.assistant.candidate;
import java.nio.file.*;
import java.util.*;
public final class DisplayCoverageTest {
    private static void check(boolean ok) {if(!ok)throw new AssertionError("Coverage policy failure");}
    public static void main(String[] args)throws Exception {
        DisplayFrame frame=DisplayFrame.parse(Files.readAllBytes(Path.of(args[0])));
        String event=frame.replies.values().iterator().next().event();
        DisplayCoverage coverage=new DisplayCoverage();coverage.layout(frame,"layout1",Map.of(event,3));
        for(DisplayCoverage.Gate gate:DisplayCoverage.Gate.values()) {
            coverage.beginPaint(frame.epoch,frame.frame,"layout1",frame.chat,frame.runtime,gate);
            for(int i=0;i<3;i++)coverage.segment(event,i);
            check(coverage.finishPaint().equals(gate==DisplayCoverage.Gate.VISIBLE?List.of(event):List.of()));
        }
        // A partial first paint cannot combine with a later partial scroll/repaint.
        coverage.beginPaint(frame.epoch,frame.frame,"layout1",frame.chat,frame.runtime,DisplayCoverage.Gate.VISIBLE);
        coverage.segment(event,0);coverage.segment(event,0);check(coverage.finishPaint().isEmpty());
        coverage.beginPaint(frame.epoch,frame.frame,"layout1",frame.chat,frame.runtime,DisplayCoverage.Gate.VISIBLE);
        coverage.segment(event,1);coverage.segment(event,2);check(coverage.finishPaint().isEmpty());
        for(int mismatch=0;mismatch<5;mismatch++) {
            coverage.beginPaint(mismatch==0?UUID.randomUUID().toString():frame.epoch,
                mismatch==1?UUID.randomUUID().toString():frame.frame,mismatch==2?"layout2":"layout1",
                mismatch==3?UUID.randomUUID().toString():frame.chat,mismatch==4?UUID.randomUUID().toString():frame.runtime,DisplayCoverage.Gate.VISIBLE);
            for(int i=0;i<3;i++)coverage.segment(event,i);check(coverage.finishPaint().isEmpty());
        }
        coverage.beginPaint(frame.epoch,frame.frame,"layout1",frame.chat,frame.runtime,DisplayCoverage.Gate.VISIBLE);
        for(int i=0;i<3;i++)coverage.segment(event,i);coverage.cancel();check(coverage.finishPaint().isEmpty());
        coverage.beginPaint(frame.epoch,frame.frame,"layout1",frame.chat,frame.runtime,DisplayCoverage.Gate.VISIBLE);
        coverage.segment(event,0);
        try{coverage.segment(event,3);throw new AssertionError("Expected invalid segment refusal");}
        catch(IllegalArgumentException expected){}check(coverage.finishPaint().isEmpty());
        try{coverage.layout(frame,"layout2",Map.of(event,4097));throw new AssertionError("Expected budget refusal");}
        catch(IllegalArgumentException expected){}check(coverage.finishPaint().isEmpty());
        try{coverage.layout(frame,"layout2",Map.of(UUID.randomUUID().toString(),1));throw new AssertionError("Expected foreign event refusal");}
        catch(IllegalArgumentException expected){}check(coverage.finishPaint().isEmpty());
        System.out.println("coverage policy passed; no native visibility claim");
    }
}
