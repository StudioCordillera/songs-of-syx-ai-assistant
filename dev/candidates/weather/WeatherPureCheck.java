import syx.assistant.candidate.WeatherObservation;
import java.util.*;
public final class WeatherPureCheck {
    public static void main(String[] ignored){
        int rejected=0;
        for(double value:new double[]{0,.5,1}){
            double[] f=new double[10];Arrays.fill(f,value);
            var d=WeatherObservation.detached(f,new boolean[]{true,false,true,false});
            Map<?,?> values=(Map<?,?>)d.get("factors");
            if(values.size()!=10 || !new ArrayList<>(values.keySet()).equals(WeatherObservation.FACTORS) || !values.values().stream().allMatch(v->v.equals(value)))throw new AssertionError();
        }
        for(double invalid:new double[]{Double.NaN,Double.POSITIVE_INFINITY,Double.NEGATIVE_INFINITY,-.001,1.001})for(int i=0;i<10;i++){
            double[] f=new double[10];f[i]=invalid;
            try{WeatherObservation.detached(f,new boolean[4]);throw new AssertionError();}catch(IllegalArgumentException expected){rejected++;}
        }
        for(int n:new int[]{0,9,11})try{WeatherObservation.detached(new double[n],new boolean[4]);throw new AssertionError();}catch(IllegalArgumentException expected){rejected++;}
        for(int n:new int[]{0,3,5})try{WeatherObservation.detached(new double[10],new boolean[n]);throw new AssertionError();}catch(IllegalArgumentException expected){rejected++;}
        try{WeatherObservation.detached(null,new boolean[4]);throw new AssertionError();}catch(IllegalArgumentException expected){rejected++;}
        try{WeatherObservation.detached(new double[10],null);throw new AssertionError();}catch(IllegalArgumentException expected){rejected++;}
        if(rejected!=58)throw new AssertionError();
        System.out.println("WEATHER PURE: accepted=3 rejected="+rejected+" no_game_initialization=true");
    }
}
