package syx.assistant;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import game.GAME;
import game.VERSION;
import init.resources.RESOURCE;
import init.resources.RESOURCES;
import world.WORLD;
import world.map.regions.Region;
import world.region.RD;
import world.region.RDOutputs.RDResource;
import static syx.assistant.StateCollector.object;

/** Fixed resource-output request, parsed off-thread and read only on GAME.addAfterUpdate. */
public final class RegionalReadRequest {
    public final String id,session;
    final long expires;final int cursor,scanLimit,limit;final boolean capture;
    final List<Integer> regionIds;final List<String> resourceIds;final Set<String> fields;
    final Integer minimum,maximum,faction;
    private static final Set<String> KEYS=Set.of("protocol","request_id","session","expires","regions","resources","fields","cursor","scan_limit","limit","minimum","maximum","faction");
    private static final Set<String> FIELDS=Set.of("accrued_output_raw","days_until_configured_output","reference_id","faction_id");
    private static int integer(String value,int low,int high) {
        if(!value.matches("0|[1-9][0-9]*"))throw new IllegalArgumentException("Invalid integer");
        int n=Integer.parseInt(value);if(n<low || n>high)throw new IllegalArgumentException("Integer out of range");return n;
    }
    private static Integer optional(String value){return value.isEmpty()?null:integer(value,0,Integer.MAX_VALUE);}
    private static String uuid(String value){if(!UUID.fromString(value).toString().equals(value))throw new IllegalArgumentException("Noncanonical UUID");return value;}
    private static String key(String value) {
        byte[] bytes=Base64.getUrlDecoder().decode(value);String text=new String(bytes,StandardCharsets.UTF_8);
        if(text.isEmpty() || text.codePointCount(0,text.length())>100 || !Base64.getUrlEncoder().withoutPadding().encodeToString(text.getBytes(StandardCharsets.UTF_8)).equals(value))
            throw new IllegalArgumentException("Invalid resource key");
        return text;
    }
    public static RegionalReadRequest parse(String text) {
        if(text.length()>8192 || !text.endsWith("\n") || text.endsWith("\n\n") || text.indexOf('\r')>=0)
            throw new IllegalArgumentException("Invalid request framing");
        Map<String,String> values=new HashMap<>();
        for(String line:text.split("\n")) {
            int at=line.indexOf('=');if(at<1)throw new IllegalArgumentException("Invalid request line");
            String k=line.substring(0,at);
            if(!KEYS.contains(k) || values.put(k,line.substring(at+1))!=null)throw new IllegalArgumentException("Unknown or duplicate request field");
        }
        if(!values.keySet().equals(KEYS) || !Set.of("1","2").contains(values.get("protocol")))throw new IllegalArgumentException("Unsupported regional protocol");
        return new RegionalReadRequest(values);
    }
    private RegionalReadRequest(Map<String,String> p) {
        id=uuid(p.get("request_id"));session=uuid(p.get("session"));capture="2".equals(p.get("protocol"));
        if(!p.get("expires").matches("[0-9]{13}"))throw new IllegalArgumentException("Invalid deadline");
        expires=Long.parseLong(p.get("expires"));if(expires-System.currentTimeMillis()>15000)throw new IllegalArgumentException("Deadline too far ahead");
        regionIds=new ArrayList<>();resourceIds=new ArrayList<>();
        for(String value:p.get("regions").split(",",-1)) {
            int n=integer(value,0,1022);if(regionIds.contains(n))throw new IllegalArgumentException("Duplicate region");regionIds.add(n);
        }
        for(String value:p.get("resources").split(",",-1)) {
            String k=key(value);if(resourceIds.contains(k))throw new IllegalArgumentException("Duplicate resource");resourceIds.add(k);
        }
        if(regionIds.size()>100 || resourceIds.size()>100)throw new IllegalArgumentException("At most 100 region/resource IDs");
        fields=new LinkedHashSet<>(Arrays.asList(p.get("fields").split(",",-1)));
        if(!FIELDS.containsAll(fields) || fields.size()!=p.get("fields").split(",",-1).length)throw new IllegalArgumentException("Invalid projection");
        cursor=integer(p.get("cursor"),0,regionIds.size()*resourceIds.size());
        scanLimit=integer(p.get("scan_limit"),1,capture?10000:4096);limit=integer(p.get("limit"),1,capture?2000:100);
        if(capture && (cursor!=0 || regionIds.size()*resourceIds.size()>scanLimit))throw new IllegalArgumentException("Capture matrix must fit one bounded callback from cursor zero");
        minimum=optional(p.get("minimum"));maximum=optional(p.get("maximum"));faction=optional(p.get("faction"));
        if(minimum!=null && maximum!=null && minimum>maximum)throw new IllegalArgumentException("Invalid accrued range");
    }
    private Map<String,Object> error(String actual,String reason) {
        return object("request_id",id,"session_id",actual,"game_version",VERSION.VERSION_STRING,
            "captured_at",Instant.now().toString(),"available",false,"reason",reason,"data",null);
    }
    public Map<String,Object> collect(String actual) {
        if(!actual.equals(session))return error(actual,"Session changed; rediscover game state");
        if(System.currentTimeMillis()>expires)return error(actual,"Regional request expired");
        if(!WORLD.GEN().isDone)return error(actual,"No completed campaign world");
        try {
            var active=WORLD.REGIONS().active();
            if(active.size()>1023 || RESOURCES.ALL().size()>1000)throw new IllegalArgumentException("Registry scan bound exceeded");
            Map<Integer,Region> regionMap=new HashMap<>();
            for(Region region:active)if(regionIds.contains(region.index())) {
                if(regionMap.put(region.index(),region)!=null)throw new IllegalArgumentException("Ambiguous active region ID");
            }
            Map<String,RDResource> outputMap=new HashMap<>();
            for(RESOURCE resource:RESOURCES.ALL())if(resourceIds.contains(resource.key)) {
                var tradable=init.trade.TR.get(resource);var output=RD.OUTPUT().get(tradable);
                if(output.res!=tradable || outputMap.put(resource.key,output)!=null)throw new IllegalArgumentException("Ambiguous resource binding");
            }
            if(regionMap.size()!=regionIds.size())throw new IllegalArgumentException("Unknown or inactive requested region");
            if(outputMap.size()!=resourceIds.size())throw new IllegalArgumentException("Unknown requested resource key");
            int next=cursor,scanned=0,errors=0,area=regionIds.size()*resourceIds.size();List<Object> rows=new ArrayList<>();
            while(next<area && scanned<scanLimit && (capture || rows.size()<limit)) {
                int rid=regionIds.get(next/resourceIds.size());String resource=resourceIds.get(next%resourceIds.size());next++;scanned++;
                try {
                    Region region=regionMap.get(rid);RDResource output=outputMap.get(resource);
                    Integer owner=null,value=null;
                    if(faction!=null || fields.contains("faction_id")) {var f=region.faction();owner=f==null?null:f.index();}
                    if(faction!=null && !faction.equals(owner))continue;
                    if(minimum!=null || maximum!=null || fields.contains("accrued_output_raw")) {
                        value=output.yearlyAccumilation.get(region);if(value<0)throw new IllegalStateException("Negative stored output counter");
                        if(minimum!=null && value<minimum || maximum!=null && value>maximum)continue;
                    }
                    Map<String,Object> row=object("region_id",rid,"resource_id",resource);
                    for(String field:fields)switch(field) {
                        case "accrued_output_raw":row.put(field,value);break;
                        case "days_until_configured_output":int days=output.daysUntilDailydelivery();if(days<0)throw new IllegalStateException("Negative configured offset");row.put(field,days);break;
                        case "reference_id":row.put(field,"resource:"+resource);break;
                        case "faction_id":row.put(field,owner);break;
                        default:throw new IllegalArgumentException("Unknown field");
                    }
                    if(capture && rows.size()>=limit)return error(actual,"Regional capture exceeds max_rows; no selection retained. Narrow IDs/filters or increase max_rows within limits.");
                    rows.add(row);
                } catch(RuntimeException failure){errors++;}
            }
            if(capture && (next<area || errors!=0))return error(actual,"Incomplete regional capture; no selection retained. Narrow IDs/filters or increase max_rows within limits.");
            return object("request_id",id,"session_id",actual,"game_version",VERSION.VERSION_STRING,"captured_at",Instant.now().toString(),
                "tick",Math.max(0,GAME.updateI()),"observer_phase","GAME.addAfterUpdate","read_mode",capture?"regional_capture":"regional_page","available",true,
                "scope","campaign_world_regions","coverage","partial","scene",UiContextCollector.scene(),"ui_context",UiContextCollector.collect(),
                "data",object("rows",rows,"scanned_cells",scanned,"cell_errors",errors,"next_cursor",next<area?next:null,
                    "cursor_kind","requested_region_resource_matrix","region_ids",regionIds,"resource_ids",resourceIds,
                    "scanned_regions",active.size(),"scanned_resources",RESOURCES.ALL().size(),"region_scan_limit",1023,"resource_scan_limit",1000),
                "consistency","One live callback per page; requested matrix positions are cursors, not matching-row counts. Pages are separate observations, not a retained/global transaction.",
                "reason","Stored resource-backed campaign accrual and cyclic configured offset only. Not inventory, annual delivered totals, income/production forecast, selected region or actual shipping/arrival ETA. Exact age is unknown. Cell errors make matching absence/count unknown.");
        } catch(RuntimeException failure){return error(actual,failure.getClass().getSimpleName()+": "+failure.getMessage());}
    }
}
