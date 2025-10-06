from typing import Tuple
LEX = {"sad":{"sad","down","depressed","blue"},
       "nervous":{"nervous","worried","uneasy","concerned"},
       "anxious":{"anxious","panic","overwhelmed"},
       "angry":{"angry","furious","annoyed","irritated"},
       "frustrated":{"frustrated","stuck","blocked"},
       "happy":{"happy","glad","joyful","cheerful"},
       "excited":{"excited","pumped","thrilled"}}
INTENS={"very","really","so","super","extremely","quite"}
NEG={"not","no","never"}
def classify(text:str)->Tuple[str,float]:
    if not text: return "neutral",0.5
    t=text.lower().split(); best=("neutral",0.5)
    for i,w in enumerate(t):
        for k,vs in LEX.items():
            if w in vs:
                inten=0.6
                win=t[max(0,i-2):i]
                if any(x in INTENS for x in win): inten+=0.2
                if any(x in NEG for x in win): k="neutral"; inten=0.5
                inten=max(0,min(1,inten))
                if inten>best[1]: best=(k,inten)
    return best
