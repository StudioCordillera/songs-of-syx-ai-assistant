package syx.assistant.candidate;

import java.util.*;

/** Bounded plain status rows; detached from native display/read receipts. */
public final class StatusLines {
    public static final int MAX_CODE_POINTS=4096,MAX_ROWS=64;
    public static final String OMITTED="[Long status shortened]";
    public static List<String> wrap(String text,int columns){
        if(text==null||columns<1||columns>8192)throw new IllegalArgumentException("Bounded status columns required");
        List<String> rows=new ArrayList<>();StringBuilder line=new StringBuilder();
        int offset=0,count=0,width=0;
        int dataRows=MAX_ROWS-(OMITTED.length()+columns-1)/columns;
        while(offset<text.length()&&count<MAX_CODE_POINTS&&rows.size()<dataRows){
            int cp=text.codePointAt(offset);offset+=Character.charCount(cp);count++;
            if(Character.isISOControl(cp))cp=' ';
            line.appendCodePoint(cp);width++;
            if(width==columns){rows.add(line.toString());line.setLength(0);width=0;}
        }
        if(line.length()>0)rows.add(line.toString());
        if(offset<text.length()){
            // Wrap the omission marker too; every row must fit the same measured width.
            for(int i=0;i<OMITTED.length()&&rows.size()<MAX_ROWS;i+=columns)
                rows.add(OMITTED.substring(i,Math.min(i+columns,OMITTED.length())));
        }
        if(rows.isEmpty())rows.add("");
        return List.copyOf(rows);
    }
}
