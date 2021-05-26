from .b import Hello
from jedi import Script

print(Hello())
print(Script)

def Hello():
    x = "Gotcha"
    return x

print(Hello())

def Hello():
    return "stop naming things the same"

print(Hello())
