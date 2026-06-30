from aura_att_fst_runtime import load_ojibwe_transducer, load_error

t = load_ojibwe_transducer()
if t:
    print("FST loaded successfully")
    for word in ["nibaa", "boozhoo", "miigwech", "aki", "nimishoomis", "nookomis"]:
        results = t.analyse(word)
        display = results[:2] if results else ["(no analysis)"]
        print(f"  {word}: {display}")
else:
    print("FST load failed:", load_error())
