# Nova v2

Nova v2 is a batteries-included interpreted programming language written in pure Python.

## Requirements
Python 3.10+

## Run
python nova.py examples/hello.nova

## REPL
python nova.py

## Debug
python nova.py --tokens examples/hello.nova
python nova.py --ast examples/hello.nova

## Features

Variables, constants, functions, lambdas, recursion, closures, classes, objects, constructors, inheritance, methods, arrays, maps, sets, ranges, indexing, slicing, destructuring, if/else, while, for, try/catch/finally, throw, break, continue, imports, modules, file IO, JSON, string interpolation, operators, ternary expressions, null coalescing, pipes, comprehensions, generators, decorators, async-style task helpers, and a large standard library.

## Examples

python nova.py examples/hello.nova
python nova.py examples/classes.nova
python nova.py examples/advanced.nova

## Syntax

let x = 10
const name = "Nova"
x = x + 1

fn add(a, b) {
    return a + b
}

class User {
    init(name) {
        self.name = name
    }
    greet() {
        return "Hello " + self.name
    }
}

let u = User("Nova")
say u.greet()

if x > 5 {
    say "large"
} else {
    say "small"
}

for x in range(5) {
    say x
}

try {
    throw "problem"
} catch err {
    say err
} finally {
    say "done"
}

## CLI

python nova.py file.nova
python nova.py --tokens file.nova
python nova.py --ast file.nova
python nova.py --check file.nova

Nova source files use the .nova extension.
old v1 : https://github.com/logicnestxvoidlure/nova-v1
