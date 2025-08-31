# Command: new-account

**Description:**
Manage the whitelist to allow new accounts to join the server. This command is for server admins.

**Usage:**

```text
.taco new-account [command]
!taco new-account [command]
?taco new-account [command]
```

## Subcommands


### whitelist-add

- **Description:** Adds a user to the whitelist to allow a 'new account' to join the server.

- **Usage:**

```text
.taco new-account whitelist-add <userID>
!taco new-account whitelist-add <userID>
?taco new-account whitelist-add <userID>
```

- **Example:**

```text
.taco new-account whitelist-add 123456789012345678
```

- **Admin Only:** Yes


### whitelist-remove

- **Description:** Removes a user from the whitelist to prevent a 'new account' from joining the server.

- **Usage:**

```text
.taco new-account whitelist-remove <userID>
!taco new-account whitelist-remove <userID>
?taco new-account whitelist-remove <userID>
```

- **Example:**

```text
.taco new-account whitelist-remove 123456789012345678
```

- **Admin Only:** Yes
