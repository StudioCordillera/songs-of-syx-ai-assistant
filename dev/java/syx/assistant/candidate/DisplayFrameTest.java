package syx.assistant.candidate;

import java.nio.file.*;
import java.util.*;

/** Test-only shared-wire corpus driver; never packaged with the game mod. */
public final class DisplayFrameTest {
    public static void main(String[] args)throws Exception {
        int accepted=0,rejected=0;
        for(String spec:Files.readAllLines(Path.of(args[0]))) {
            String[] parts=spec.split(" ");byte[] raw=Files.readAllBytes(Path.of(parts[1]));DisplayFrame frame;
            try {frame=DisplayFrame.parse(raw);}
            catch(IllegalArgumentException bad) {if(!parts[0].equals("reject"))throw bad;rejected++;continue;}
            if(!parts[0].equals("accept"))throw new AssertionError("Invalid frame accepted: "+parts[1]);
            String expected=parts[2];if(!Objects.equals(expected,frame.total==null?"unknown":frame.total.toString()))throw new AssertionError("Wrong count");
            if(frame.replies.size()!=Integer.parseInt(parts[3]))throw new AssertionError("Wrong reply provenance count");
            if(frame.total==null&&!frame.badge().equals("?"))throw new AssertionError("Unknown badge rendered as zero");
            if(frame.total!=null&&frame.total>99&&!frame.badge().equals("99+"))throw new AssertionError("Badge not visually capped");
            accepted++;
        }
        if(args.length==3) {
            DisplayFrame frame=DisplayFrame.parse(Files.readAllBytes(Path.of(args[1])));
            DisplayFrame.Reply first=frame.replies.values().stream().min(Comparator.comparingInt(DisplayFrame.Reply::row)).orElseThrow();
            Files.write(Path.of(args[2]),frame.receipt(List.of(first.event()),first.observedSession(),"00000000-0000-4000-8000-000000000001"));
            boolean rejectedForeign=false;
            try {frame.receipt(List.of("00000000-0000-4000-8000-000000000002"),first.observedSession(),"00000000-0000-4000-8000-000000000001");}
            catch(IllegalArgumentException expected){rejectedForeign=true;}
            if(!rejectedForeign)throw new AssertionError("Unissued receipt event accepted");
        }
        System.out.println("PASS accepted="+accepted+" rejected="+rejected);
    }
}
