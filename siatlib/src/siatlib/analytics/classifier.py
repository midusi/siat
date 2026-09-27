import math
from collections import Counter
from typing import List, Dict, Tuple

def calculate_entropy(track_data: List[Dict]) -> Tuple[Counter, float]:
    """Calcula la entropía de Shannon para las clasificaciones de un objeto a lo largo de su seguimiento."""
    total_track = len(track_data)
    if total_track == 0:
        return Counter(), 0.0

    class_counts = Counter()
    for item in track_data:
        class_counts[item['class_id']] += 1
    
    probabilities = [count / total_track for class_id, count in class_counts.items()]
    entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
    
    return class_counts, entropy

def classify_track(class_counts: Counter, class_names_mapping: Dict[int, str]) -> str:
    """Determina la clase final de un objeto basándose en su historial de clasificaciones."""
    if not class_counts:
        return "indeterminado"
        
    assigned_class_id = max(class_counts, key=class_counts.get)
    return class_names_mapping.get(assigned_class_id, "indeterminado")
