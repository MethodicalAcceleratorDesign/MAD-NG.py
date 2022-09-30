import numpy as np

#TODO: Make each madObject have a list of objects that obeys a print function
#TODO: Make dot overload more stable -> Could you load a module and instead only overload the dot for everything within the module?

class madObject(object):
    def __init__(self, name, mad):
        self.name = name
        self.mad = mad

    def __getattribute__(self, item):
        if item in ["mad", "name", "__class__", "attachedElements", "attributes", "iterVars", "iterIndex", "__dict__"]: 
            return super(madObject, self).__getattribute__(item)
        self.mad.receiveVariables([self.name +"."+ item])
        return self.mad.__getattribute__(self.name +"."+ item)

    def __setattr__(self, item, value):
        if item in ["mad", "name", "__class__", "attachedElements", "attributes", "iterVars", "iterIndex", "__dict__"]:
            return super(madObject, self).__setattr__(item, value)
        if isinstance(value, madObject):
            if self.mad.writeToProcess(f"do {self.name + '.' + item} = {value.name} end") != 5: raise(RuntimeError(self.mad.process.match.group(0)))
        elif isinstance(value, np.ndarray):
            self.mad.sendVar(self.name +"."+ item, value)

    def __getitem__(self, item: str):
        self.mad.receiveVariables([self.name +"."+ item])
        return self.mad.__getattribute__(self.name +"."+ item)
    
    def __setitem__(self, item, value):
        if isinstance(value, madObject):
            self.mad.writeToProcess(f"do {self.name + '.' + item} = {value.name} end")
        elif isinstance(value, np.ndarray):
            self.mad.sendVar(self.name +"."+ item, value)

class madElement(madObject):
    attributes = ["l", "lrad", "angle", "tilt", "model", "method", "nslice", "misalign", "apertype"]
    def __init__(self, name, mad):
        self.name = name
        self.mad = mad
        def getKwargAsString(**kwargs):
            kwargList = [x.split(',')[-1].replace("'", "") for x in str(kwargs).split(":")[:-1]] #Replace all the ' in the args (could split up?)
            kvalsList = [x.split(',')[0] for x in str(kwargs).split(":")[1:]]                    #Do not replace string identifier in vals
            kwargsString = ",".join([kwargList[x] + " =" + kvalsList[x] for x in range(len(kwargList))])
            return kwargsString
        returnElm = lambda funcName = name, **kwargs: f"""{name} '{funcName}' {getKwargAsString(**kwargs)}"""
        setattr(mad, name + "Set", returnElm)
    
    def __iter__(self):
        self.iterVars = [self.name + "." + attr for attr in self.attributes]
        self.iterIndex = 0
        self.mad.receiveVariables(self.iterVars)
        return self
    
    def __next__(self):
        while self.iterIndex < len(self.attributes):
            attr = self.mad[self.name + "." + self.attributes[self.iterIndex]]
            self.iterIndex += 1
            return {self.attributes[self.iterIndex-1]: attr}
        raise StopIteration

class deferred(madObject):
    pass