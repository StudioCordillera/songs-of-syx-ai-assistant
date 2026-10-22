package syx.assistant.candidate;

public final class StatusLinesProbe {
    private static void check(boolean value){if(!value)throw new AssertionError();}
    public static void main(String[] args){
        for(int columns:new int[]{1,2,7,37,80,8192}){
            String text="猫🌲 café\n".repeat(900);
            var rows=StatusLines.wrap(text,columns);
            check(rows.size()<=StatusLines.MAX_ROWS);
            check(String.join("",rows).endsWith(StatusLines.OMITTED));
            for(String row:rows){
                check(row.codePointCount(0,row.length())<=columns);
                check(!row.contains("\n"));
                for(int i=0;i<row.length();i++){
                    if(Character.isHighSurrogate(row.charAt(i))){check(i+1<row.length()&&Character.isLowSurrogate(row.charAt(++i)));}
                    else check(!Character.isLowSurrogate(row.charAt(i)));
                }
            }
        }
        check(String.join("",StatusLines.wrap("Earlier reply interrupted; no automatic retry.",17)).equals("Earlier reply interrupted; no automatic retry."));
        check(StatusLines.wrap("",30).size()==1);
        check(StatusLines.wrap("a\r\t\nb",20).get(0).equals("a   b"));
        for(int invalid:new int[]{0,-1,8193}){
            try{StatusLines.wrap("text",invalid);throw new AssertionError();}catch(IllegalArgumentException expected){}
        }
        System.out.println("PASS bounded status rows, explicit omission, control spacing and Unicode boundaries");
    }
}
