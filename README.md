Based on the https://github.com/rustwasm/wasm-pack-template.git

# About

This project uses wasm-build and webpack-dev-server together to serve a wasm binary compiled from a domain-specific syntax called [CUI](https://github.com/thisminute/cascading-ui).

CUI compiles into HTML and a Wasm binary. This repository is basically a customized [wasm-pack-template](Based on the https://github.com/rustwasm/wasm-pack-template.git) for use with CUI. After installation, modify the source code in `src/lib.rs`, and run `npm install` and `npm start` to build the page and show it in a browser.

# Install

To install, you will need:

1. [rustc/cargo](https://www.rust-lang.org/tools/install)
1. [node/npm](https://nodejs.org/en/download/)
1. [wasm-pack](https://rustwasm.github.io/wasm-pack/installer/)

Then:

```
git clone https://github.com/thisminute/cui-app-template.git
```

For windows users, run in the root directory:

```bash
rustup toolchain install stable-x86_64-pc-windows-gnu
rustup default stable-x86_64-pc-windows-gnu
```

Then:

```
cd cui-app-template
npm run build # has to be run before install for npm to install cui
npm install
npm start # opens a new browser tab in watch mode
```

# Cascading UI

Cascading UI is named for the Cascading in Cascading Style Sheets, which it borrows its basic syntax from. CUI has classes like CSS:

```cui
.my-class {
   color: "red";
   text: "hello world"; // some different properties from css
}
```

This block says that all elements of class `my-class` should say "hello world" in red text. CUI borrows the syntax of CSS but also extends it to specifying the content of a page or creating elements (compiling to HTML), and adding behavior to a page (compiling to Webassembly, taking the traditional role of Javascript).

```cui
my-class {
   color: "green";
}
```

This block type, without a `.` at the beginning, would create an element, and then modify the properties of that element directly. If both blocks set the same property, the property in the _element block_ would override the property in the _class block_. In this case, if this was used with the first code block, there will be just one element, and it will say "hello world" in green text. Writing `my-class {}` with no properties is similar to writing `<div class="my-class"></div>` in html, and setting the color inside of the block is similar to overwriting the class property with an inline style (or exactly that, in the case of css properties).

```cui
?click {
   color: "blue";
}
```

This last block type is a listener block, which starts with a `?` followed by an event name, rather than a class name. Listener blocks apply to a single parent element when the event with the specified name fires with that element as the target (in this case, if the element is clicked). A CUI project with this listener at the root level would set the page to have blue text when the page was clicked, since the page itself would be the parent. Common/standard event names are built in, such as `click`, `focus`, `mouseover`, etc.

To understand the syntax of listeners, it may be helpful to think of them as changing the time at which their contents apply, but not having a role in structure directly. The example listener is still a statement about the color of the page, just at a future time, when it has been clicked. If the listener has structure (at least one instance block) in it, that structure will overwrite the structure of the parent when the listener is triggered. Variables and data are to be used if the structure needs to be modified instead of being replaced.

Like Sass or other extensions of CSS, CUI supports nesting blocks inside of each other. Unlike Sass, however, we have these three different types of blocks: class blocks, element blocks, and listener blocks. A class block inside of another class block is different from a listener block to inside of an element block. Let's look at the basic blocks one more time together and then look at the nesting patterns:

### Basic blocks

```cui
// class
// apply the rules to all descendants of class "a"
// NOTE: descendants include both current and future matching elements
.a {
   // rules
}

// element
// create an element of class "a" and apply the rules to it
a {
   // rules
}

// listener
// apply the rules to the parent when it is clicked
?click {
   // rules
}
```

### Nesting patterns

```cui
// class in class
// in all descendants of class "a", apply the rules to all of their descendants of class "b"
.a {
   .b {
      // rules
   }
}

// class in element
// create an element of class "a" and apply the rules to all of its descendants of class "b"
a {
   .b {
      // rules
   }
}

// element in element
// create an element of class "a", then create an element of class "b" inside it with the rules applied
// NOTE: can conflict with elements in other blocks (see [Structures](#structures))
a {
   b {
      // rules
   }
}

// element in class
// in all descendants of class "a", create an element of class "b" with the rules applied
// NOTE: can conflict with elements in other blocks (see [Structures](#structures))
.a {
   b {
      // rules
   }
}

// listener in class
// apply the rules to any descendant of class "a" when it is clicked
.a {
   ?click {
      // rules
   }
}

// class in listener
// when the parent is clicked, apply the rules to its descendants of class "a"
?click {
   .a {
      // rules
   }
}

// listener in element
// create an element of class "a" and apply the rules to it when it is clicked
a {
   ?click {
      // rules
   }
}

// element in listener
// when the parent is clicked, replace its structure (see [Structures](#structures)) with an element of class "a"  with the rules applied
?click {
   a {
      // rules
   }
}

// listener in listener
// the parent gains a mouseover listener when clicked, after which the parent will have the rules applied to it when it is moused over
?click {
   ?mouseover {
      // rules
   }
}
```

# Structures

Any block that contains at least one element block defines some structure that will apply to an element. An error is thrown during a build if multiple blocks define a structure at the same time. The word "time" is important here, because listeners can overwrite structures, but with only one structure at a time. For any listener, the effects must never write more than one structure to an element, and outside of listeners, every element must only have its structure specified in one place. For example:

```cui
.a {
   // these two lines specify that all elements of class "a" contain a structure consisting of 2 elements of class "b"
   b {}
   b {}
}
a {
   c {} // this specifies a different structure, causing an error
}
```

However changing the structure over time, with listeners, is okay:

```cui
a {
   b {} // this specifies a structure
   ?click {
      c { // clicking the element will change the structure to this element with another element in it
         d {}
      }
   }
   ?mouseover {
      c {} // mousing over the element it replaces the structure with this empty element of class "c"
   }
}
```

To use a listener to modify a structure instead of replacing it, you will need variables.

# Variables

To be implemented...

Without variables, we can turn any element of class "a" green when it is clicked:

```cui
.a {
   text: "hello world";
   color: "red";
   ?click {
      color: "green";
   }
}
a {}
a {}
```

But to make all elements of class "a" green when any of them are clicked, we need variables:

```cui
$color: "red";
.a {
   text: "hello world";
   color: $color;
   ?click {
      $color: "green";
   }
}
a {}
a {}
```
