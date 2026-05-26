--- 
name: Version Control
description: "Manage adapter versions"
version: 1.0.0  
---

# When use skill
When you change the adapter code

# Goal
- Control the version of the adapter, so that when the adapter code changes, we can decide whether to re-adapt the files or not.

# Implementation
- Each adapter has a `version` property that returns an integer.
- If the adapter code changes, we increment the version number.