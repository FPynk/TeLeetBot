# return weight values as tuple
def parse_weights(weights_str:str) -> tuple[int,int,int]:
    try:
        e,m,h = map(int, weights_str.split(","))
        return e,m,h
    except Exception:
        return (1,2,5)

# calculate total score = problem qty * difficult point weightage
def score_counts(counts:dict[str,int], weights:tuple[int,int,int]) -> int:
    e,m,h = weights
    return counts.get('Easy',0)*e + counts.get('Medium',0)*m + counts.get('Hard',0)*h
