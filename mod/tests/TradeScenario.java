import java.nio.file.*;
import java.util.*;
import game.GAME;
import init.resources.RESOURCES;
import init.trade.TRADE_TYPE;
import snake2d.CORE;
import syx.assistant.JsonWriter;

/** TEST ONLY: seeds public bookkeeping in a paused copied game; never writes a save. */
public final class TradeScenario {
    public static void install(Path directory) {
        GAME.SPEED.speedSet(0);long began=System.currentTimeMillis();boolean[] ready={false};
        GAME.addAfterUpdate(()->{
            try {
                if(!ready[0] && System.currentTimeMillis()-began>10000) {
                    ready[0]=true;var first=RESOURCES.ALL().get(0);var buyer=GAME.player().buyer(first.tr());var seller=GAME.player().seller(first.tr());
                    int reserved=buyer.toBeAdded().get(TRADE_TYPE.trade),pending=buyer.toBeStored().get(TRADE_TYPE.trade);
                    int taxed=buyer.toBeAdded().get(TRADE_TYPE.tax),promised=seller.promised().get(TRADE_TYPE.trade);
                    buyer.addReserve(7,TRADE_TYPE.trade,0,GAME.player());buyer.addDeliver(3,TRADE_TYPE.trade);
                    buyer.addReserve(2,TRADE_TYPE.tax,0,GAME.player());seller.remove(5,TRADE_TYPE.trade,0,GAME.player());
                    buyer.priceCapsI.set(47);buyer.minMoney.set(123);buyer.limit.set(40);seller.priceCapsI.set(23);seller.limit.set(35);
                    if(buyer.toBeAdded().get(TRADE_TYPE.trade)-reserved!=4 || buyer.toBeStored().get(TRADE_TYPE.trade)-pending!=3 ||
                       buyer.toBeAdded().get(TRADE_TYPE.tax)-taxed!=2 || seller.promised().get(TRADE_TYPE.trade)-promised!=5)
                        throw new IllegalStateException("Controlled bookkeeping deltas did not hold");
                    List<Object> policies=new ArrayList<>(),flows=new ArrayList<>();
                    for(var resource:RESOURCES.ALL()) {
                        var buy=GAME.player().buyer(resource.tr());var sell=GAME.player().seller(resource.tr());
                        policies.add(Map.of("resource_id",resource.key,"reference_id","resource:"+resource.key,
                            "buy_price_cap_raw",buy.priceCapsI.get(),"import_treasury_floor_credits",buy.minMoney.get(),
                            "import_level_raw",buy.limit.get(),"sell_price_floor_raw",sell.priceCapsI.get(),"export_level_raw",sell.limit.get()));
                        for(var type:TRADE_TYPE.all) {
                            Map<String,Object> row=new LinkedHashMap<>();row.put("resource_id",resource.key);row.put("trade_type_id",type.index);row.put("trade_type_name",type.name.toString());
                            row.put("inbound_reserved_units",buy.toBeAdded().get(type));row.put("inbound_pending_placement_units",buy.toBeStored().get(type));
                            row.put("inbound_caravan_units",buy.attempting(type));row.put("inbound_total_units",buy.incoming.get(type));
                            row.put("outbound_reserved_units",sell.promised().get(type));row.put("outbound_caravan_units",sell.attempting(type));row.put("outbound_total_units",sell.outbound.get(type));flows.add(row);
                        }
                    }
                    Files.writeString(directory.resolve("trade-fixture.json"),JsonWriter.encode(Map.of("policies",policies,"flows",flows,
                        "seeded_resource",first.key,"trade_reason",TRADE_TYPE.trade.index,"tax_reason",TRADE_TYPE.tax.index,
                        "fixture_note","Public reservation/delivery bookkeeping and policy setters in copied paused city, not naturally executed market orders. No save is written.")));
                    System.err.println("TRADE TEST: public getter fixture ready");
                }
                if(Files.exists(directory.resolve("verifier.done")) || System.currentTimeMillis()-began>120000)CORE.annihilate();
            }catch(Exception error){CORE.annihilate(error);}
        });
    }
}
