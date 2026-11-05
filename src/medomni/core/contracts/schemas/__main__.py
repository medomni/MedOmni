from medomni.core.contracts.schemas import write

for p in write():
    print(p.name)
