# PyStructTypes

Leverage Python Types to Define C-Struct Interfaces


# Reasoning

I made this project for 2 reasons:
1. I wanted to see if I could leverage the typing system to effectively automatically
decode and encode c-type structs in python.
2. Build a tool to do this for a separate project I am working on.

I am aware of other very similar c-type struct to python class libraries available,
but I wanted to try something new so here we are. 

This may or may not end up being super useful, as there are quite a few bits of 
hacky metaprogramming to get the type system to play nicely for what I want, but 
perhaps over time it can be cleaned up and made more useful.

# StructDataclass

The `StructDataclass` class is based off of the `Dataclass` class, and thus
is used in a similar fashion.

# Basic Structs

Basic structs can mostly be copied over 1:1

```c
struct MyStruct {
    int16_t myNum;
    char myLetter;
};
```

```python
@struct_dataclass
class MyStruct(StructDataclass):
    myNum: int16_t
    myLetter: char_t

s = MyStruct()
s.decode([4, 2, 65])
# MyStruct(myNum=1026, myLetter=b"A")
s.decode([4, 2, 65], little_endian=True)
# MyStruct(myNum=516, myLetter=b"A")
```

For arrays of basic elements, you need to Annotate them with
the `TypeMeta` object, and set their type to `list[_type_]`.

```c
struct MyStruct {
    uint8_t myInts[4];
    uint16_t myBiggerInts[2];
};
```
```python
@struct_dataclass
class MyStruct(StructDataclass):
    myInts: Annotated[list[uint8_t], TypeMeta(size=4)]
    myBiggerInts: Annotated[list[uint16_t], TypeMeta(size=2)]

s = MyStruct()
s.decode([0, 64, 128, 255, 16, 0, 255, 255])
# MyStruct(myInts=[0, 64, 128, 255], myBiggerInts=[4096, 65535])
```

You can also set defaults for both basic types and lists.

All values will default to 0 or the initialized value for the chosen class if no
specific value is set.

List defaults will set all items in the list to the same value. Currently
setting a complete default list for all values is not implemented.

```c
struct MyStruct P
    uint8_t myInt = 5;
    uint8_t myInts[2];
```

```python
@struct_dataclass
class MyStruct(StructDataclass):
    myInt: uint8_t = 5
    myInts: Annnotated[list[uint8_t], TypeMeta(size=2, default=1)]

s = MyStruct()
# MyStruct(myInt=5, myInts=[1, 1])
s.decode([10, 5, 6])
# MyStruct(myInt=10, myInts=[5, 6])
```

# The Bits Abstraction

This library includes a `bits` abstraction to map bits to variables for easier access.

One example of this is converting a C enum like so:

```c
enum ConfigFlags {
    lights_flag = 1 << 0,
    platform_flag = 1 << 1,
};
#pragma pack(push, 1)
```

```python
@bits(uint8_t, {"lights_flag": 0, "platform_flag": 1})
class FlagsType(BitsType): ...

f = FlagsType()
f.decode([3])
# FlagsType(lights_flag=True, platform_flag=True)
f.decode([2])
# FlagsType(lights_flag=False, platform_flag=True)
f.decode([1])
# FlagsType(lights_flag=True, platform_flag=False)
```

# Custom StructDataclass Processing and Extensions

There may be times when you want to make the python class do 
cool fun python class type of stuff with the data structure. 
We can extend the class functions `_decode` and `_encode` to
handle this processing.

In this example, lets say you want to be able to read/write the
class object as a list, using `__getitem__` and `__setitem__` as well
as keeping the data in a different data structure than what the 
c struct defines.

```c
struct MyStruct {
    uint8_t enabledSensors[5];
};
```

```python
@struct_dataclass
class EnabledSensors(StructDataclass):
    # We can define the actual data we are ingesting here
    # This mirrors the `uint8_t enabledSensors[5]` data
    _raw: Annotated[list[uint8_t], TypeMeta(size=5)]

    # We use this to store the data in the way we actually want
    _data: list[list[bool]] = field(default_factory=list)

    def _decode(self, data: list[int]) -> None:
        # First call the super function. This will store the raw values into `_raw`
        super()._decode(data)

        # Erase everything in self._data to remove any old data
        self._data = []

        # 2 Panels are packed into a single uint8_t, the left most 4 bits for the first
        # and the right most 4 bits for the second
        for bitlist in (list(map(bool, map(int, format(_byte, "#010b")[2:]))) for _byte in self._raw):
            self._data.append(bitlist[0:4])
            self._data.append(bitlist[4:])

        # Remove the last item in self._data as there are only 9 panels
        del self._data[-1]

    def _encode(self) -> list[int]:
        # Modify self._raw with updated values from self._data
        for idx, items in enumerate(list_chunks(self._data, 2)):
            # Last chunk
            if len(items) == 1:
                items.append([False, False, False, False])
            self._raw[idx] = sum(v << i for i, v in enumerate(list(itertools.chain.from_iterable(items))[::-1]))
            
        # Run the super function to return the encoded data from self._raw()
        return super()._encode()

    def __getitem__(self, index: int) -> list[bool]:
        # This lets us access the data with square brackets
        # ex. `config.enabled_sensors[Panel.UP][Sensor.RIGHT]`
        return self._data[index]

    def __setitem__(self, index: int, value: list[bool]) -> None:
        # Only use this to set a complete set for a panel
        # ex. `config.enabled_sensors[Panel.UP] = [True, True, False, True]`
        if len(value) != 4 or not all(isinstance(x, bool) for x in value):
            raise Exception("must set all 4 items at once")

s = EnabledSensors()
s.decode([15, 15, 15, 15, 0])

# The `self._data` here would look like:
# [
#   [False, False, False, False],
#   [True, True, True, True],
#   [False, False, False, False],
#   [True, True, True, True],
#   [False, False, False, False],
#   [True, True, True, True],
#   [False, False, False, False],
#   [True, True, True, True],
#   [False, False, False, False],
#   [False, False, False, False]
# ]

# With the get/set functioned defined, we can access the data
# with square accessors.
# s[1][2] == True 
```

# StructDataclass is Composable

You can use StructDataclasses in other StructDataclasses to create more complex
structs.

```c 
struct RGB {
    uint8_t r;
    uint8_t g;
    uint8_t b;
};

struct LEDS {
    RGB lights[3];
};
```

```python
@struct_dataclass
class RGB(StructDataclass):
    r: uint8_t
    g: uint8_t
    b: uint8_t

@struct_dataclass
class LEDS(StructDataclass):
    lights: Annotated[list[RGB], TypeMeta(size=3])]

l = LEDS()
l.decode([1, 2, 3, 4, 5, 6, 7, 8, 9])
# LEDS(lights=[RGB(r=1, g=2, b=3), RGB(r=4, g=5, b=6), RGB(r=7, g=8, b=9)])
```

# Future Updates

- Bitfield: Similar to the `Bits` abstraction. An easy way to define bitfields
- C-Strings: Make a base class to handle C strings (arrays of chars)
- Potentially more ways to define bits (dicts/lists/etc).
- Potentially allowing list defaults to be entire pre-defined lists.
- ???

# Examples

You can see a more fully fledged example in the `test/examples.py` file. 