import syx.assistant.EntityReadRequest;
import java.util.UUID;

/** Pure codec tests; no game state or UI is initialized. */
public final class EntityReadRequestTest {
    public static void main(String[] args) {
        String id=UUID.randomUUID().toString(), session=UUID.randomUUID().toString();
        String valid="protocol=1\nrequest_id="+id+"\nsession="+session+"\nexpires="+(System.currentTimeMillis()+8000)
            +"\ncursor=1001\nscan_limit=10000\nlimit=5\nids=-1,2\nrace=SFVNQU4\nclass=\ntype=\nbounds=0,0,5,5\nfields=id,stats\nstats=1,2\nfilters=1:gte:0\n";
        EntityReadRequest parsed=EntityReadRequest.parse(valid);
        if(!parsed.id.equals(id) || !parsed.session.equals(session))throw new AssertionError("Identity changed");
        String capture=valid.replace("protocol=1","protocol=2").replace("cursor=1001","cursor=0")
            .replace("limit=5","limit=2000").replace("scan_limit=10000","scan_limit=100000");
        EntityReadRequest.parse(capture);
        EntityReadRequest.parse(valid+"workplace_room_id=0\n");
        EntityReadRequest.parse(capture+"workplace_room_id=2147483647\n");
        for(String text:new String[]{capture.replace("limit=2000","limit=2001"),
            capture.replace("stats=1,2", "stats=1,2,3"),capture.replace("cursor=0","cursor=1"),
            capture.replace("fields=id,stats","fields=stats")}) {
            try {EntityReadRequest.parse(text);throw new AssertionError("Accepted invalid capture");}
            catch(IllegalArgumentException expected) { }
        }
        String[] bad={valid+"workplace_room_id=-1\n",valid+"workplace_room_id=2147483648\n",
            valid+"workplace_room_id=\n",valid+"workplace_room_id=01\n",
            valid+"workplace_room_id=0\nworkplace_room_id=1\n",valid+"method=kill\n",valid+"limit=4\n",valid.replace("scan_limit=10000","scan_limit=10001"),
            valid.replace("fields=id,stats","fields=id,privateAI"),valid.replace("limit=5","limit=100"),
            valid.replace("bounds=0,0,5,5","bounds=0,0,0,5"),valid.replace("ids=-1,2","ids=-1,-1"),
            valid.replace("filters=1:gte:0","filters=1:invoke:0"),valid.replace("race=SFVNQU4","race=%%%"),
            valid.replace("cursor=1001","cursor=2147483648"),valid.replace("protocol=1","protocol=3")};
        for(String text:bad) {
            try {EntityReadRequest.parse(text);throw new AssertionError("Accepted invalid request");}
            catch(IllegalArgumentException expected) { }
        }
        System.out.println("Entity protocol: valid request and "+bad.length+" rejection checks passed");
    }
}
