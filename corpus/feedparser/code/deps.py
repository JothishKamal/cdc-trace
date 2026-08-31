import flask
import json
import re


def warmup_bindings():
    return (flask, json, re)
