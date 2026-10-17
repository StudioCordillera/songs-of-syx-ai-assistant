import syx.assistant.TileReadRequest;
import java.util.UUID;
/** Pure framing tests; no game bootstrap or observation. */
public final class TileReadRequestTest {
    public static void main(String[] args) {
        String valid="protocol=1\nrequest_id="+UUID.randomUUID()+"\nsession="+UUID.randomUUID()+"\nexpires="+(System.currentTimeMillis()+8000)
            +"\nbounds=1,2,3,4\ncursor=0\nscan_limit=4096\nlimit=100\nfields=terrain,floor,room,minerals,path\nterrain=\nfloor=\nroom=\nmineral=\nhas_room=false\nreachable=\n";
        TileReadRequest.parse(valid);
        String[] bad={valid+"method=place\n",valid+"limit=1\n",valid.replace("protocol=1","protocol=2"),
            valid.replace("bounds=1,2,3,4","bounds=1,2,1,4"),valid.replace("bounds=1,2,3,4","bounds=1,2,3"),
            valid.replace("scan_limit=4096","scan_limit=4097"),valid.replace("limit=100","limit=101"),
            valid.replace("cursor=0","cursor=-1"),valid.replace("cursor=0","cursor=2147483648"),
            valid.replace("has_room=false","has_room=0"),valid.replace("terrain=\n","terrain=%%%\n"),
            valid.replace("fields=terrain,floor,room,minerals,path","fields=terrain,terrain"),
            valid.replace("fields=terrain,floor,room,minerals,path","fields=terrain,private"),valid.replace("floor=\n","")};
        for(String text:bad){try{TileReadRequest.parse(text);throw new AssertionError("Invalid request accepted");}catch(IllegalArgumentException expected){}}
        System.out.println("Tile protocol: valid request and "+bad.length+" invalid frames rejected");
    }
}
