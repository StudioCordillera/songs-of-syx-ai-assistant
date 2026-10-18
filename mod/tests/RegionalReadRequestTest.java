import syx.assistant.RegionalReadRequest;
import java.util.UUID;

/** Pure request codec checks; no game state/bootstrap is run. */
public final class RegionalReadRequestTest {
    public static void main(String[] args) {
        String id=UUID.randomUUID().toString(),session=UUID.randomUUID().toString();
        String text="protocol=1\nrequest_id="+id+"\nsession="+session+"\nexpires="+(System.currentTimeMillis()+8000)
            +"\nregions=0,1022\nresources=Z3JhaW4,d29vZA\nfields=accrued_output_raw,faction_id\ncursor=4\nscan_limit=4096\nlimit=100\nminimum=0\nmaximum=2147483647\nfaction=\n";
        RegionalReadRequest parsed=RegionalReadRequest.parse(text);
        if(!parsed.id.equals(id) || !parsed.session.equals(session))throw new AssertionError("Identity changed");
        String capture=text.replace("protocol=1","protocol=2").replace("cursor=4","cursor=0").replace("scan_limit=4096","scan_limit=10000").replace("limit=100\n","limit=2000\n");
        RegionalReadRequest.parse(capture);
        for(String value:new String[]{capture.replace("cursor=0","cursor=1"),capture.replace("limit=2000\n","limit=2001\n"),capture.replace("scan_limit=10000","scan_limit=3")}) {
            try{RegionalReadRequest.parse(value);throw new AssertionError("Accepted invalid capture");}catch(IllegalArgumentException expected){}
        }
        String[] bad={text+"method=ship\n",text+"limit=1\n",text.replace("protocol=1","protocol=3"),
            text.replace("regions=0,1022","regions=0,1023"),text.replace("regions=0,1022","regions=0,0"),
            text.replace("regions=0,1022","regions="),text.replace("cursor=4","cursor=5"),
            text.replace("scan_limit=4096","scan_limit=4097"),text.replace("limit=100","limit=101"),
            text.replace("minimum=0","minimum=-1"),text.replace("minimum=0","minimum=2147483648"),
            text.replace("minimum=0","minimum=10").replace("maximum=2147483647","maximum=9"),
            text.replace("resources=Z3JhaW4,d29vZA","resources=Z3JhaW4,Z3JhaW4"),
            text.replace("resources=Z3JhaW4,d29vZA","resources=Z3JhaW4=,d29vZA"),
            text.replace("resources=Z3JhaW4,d29vZA","resources=__8"),
            text.replace("fields=accrued_output_raw,faction_id","fields=private"),
            text.replace("fields=accrued_output_raw,faction_id","fields=faction_id,faction_id"),text+"\n",text.replace("\n","\r\n")};
        for(String value:bad) {
            try{RegionalReadRequest.parse(value);throw new AssertionError("Accepted invalid regional request");}
            catch(IllegalArgumentException expected) { }
        }
        System.out.println("Regional protocol: valid identity/end cursor and "+(bad.length+3)+" rejection checks passed");
    }
}
