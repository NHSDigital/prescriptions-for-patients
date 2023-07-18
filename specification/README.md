# OpenAPI Specification

## Overview
This specification has been written to provide a clear representation of our API. Both what it expects and what it will return to the client.
It conforms to the OpenAPI specification v3.1.0 found [here](https://swagger.io/specification/)

## Usage
To view the specification in a user-friendly format, you will need VSCode with the OpenAPI extension (42Crunch.vscode-openapi) installed.
You will then be able to use the `F1 > OpenAPI: show preview using ReDoc` command.

## Build
From the project root, run the following:
```
cd specification
make install
make build
```
This will output the resolved specification in json format to the /dist directory.
