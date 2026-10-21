package syx.assistant.candidate;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

/** Test-only fixed trace adapter; no game dependencies or arbitrary member invocation. */
public final class GestureTrace {
    private static double n(String s){return Double.parseDouble(s);}
    private static boolean b(String s){if(s.equals("true"))return true;if(s.equals("false"))return false;throw new IllegalArgumentException("Boolean required");}
    private static String row(String kind,GestureReducer.Rect r){
        return kind+(r==null?"\t-":"\t"+r.x+"\t"+r.y+"\t"+r.width+"\t"+r.height);
    }
    public static void main(String[] args)throws Exception{
        GestureReducer reducer=new GestureReducer();
        try(BufferedReader input=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.US_ASCII))){
            String line;
            while((line=input.readLine())!=null){
                try{
                    if(line.length()>4096)throw new IllegalArgumentException("Trace line too long");
                    String[] p=line.split("\t",-1);
                    if(p[0].equals("B") && p.length==11){
                        GestureReducer.Rect r=new GestureReducer.Rect(n(p[5]),n(p[6]),n(p[7]),n(p[8]));
                        System.out.println(row("began",reducer.begin(GestureReducer.Target.valueOf(p[1]),n(p[2]),n(p[3]),n(p[4]),r,n(p[9]),n(p[10]))));
                    }else if(p[0].equals("S") && p.length==8){
                        GestureReducer.Result r=reducer.sample(n(p[1]),n(p[2]),n(p[3]),b(p[4]),b(p[5]),n(p[6]),n(p[7]));
                        System.out.println(row(r.status,r.rect));
                    }else if(p[0].equals("C") && p.length==1){reducer.cancel();System.out.println("cancelled\t-");}
                    else throw new IllegalArgumentException("Fixed trace shape required");
                }catch(IllegalArgumentException e){System.out.println("error\t-");}
            }
        }
    }
}
