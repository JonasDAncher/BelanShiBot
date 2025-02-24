# Belan Shi Bot

Just a small Discord bot, meant to organise WoW m+ runs for my guild.

Feel free to knick it, or even make pull requests.

# How to use.

The bot has two commands; [/key](#key) and [/roles](#roles).

## Key
The /key command is the main command. It is what users can start a group with. It has 2 required fields, and 4 optional ones.\
![The key message](/readme_pictures/key_normal.jpg)
![Required fields](/readme_pictures/command_menu.jpg)

### Required fields
The two required fields are `dungeon-name` and `key-level`.

- `dungeon-name` should reflect the dungeon the group was created to run. However, no requirements as to what can go in the field, meaning any string is accepted to better reflect any servers potential colloquialisms. `Any` could also reflect a willingness to run any key.

- `key-level` should reflect the level of the key being run. If the input is >99, it will show up as `Any` in the bot's message.

### Optional fields

- `tank` can be set to `0` to indicate whether or not the Tank role is pre-filled. If set to `0`, no ping will be sent to the Tank role.

- `healer` can be set to `0` to indicate whether or not the Healer role is pre-filled. If set to `0`, no ping will be sent to the Healer role.

- `dps` can be set to `0`, `1`, `2`, or `3` to indicate how many DPS roles are pre-filled. If set to `0`, no ping will be sent to the DPS role.

- `time` should be used to indicate at what time the key run start. This field has no restrictions, no time convertions, and no checks.

## Key buttons
The resulting message has 5 buttons attached: `Tank`, `Healer`,`DPS`, `CANCEL`, and `LOCK RUN`.

### Role Buttons
The first three are the role buttons, which user can press to sign up for that role. When pressed, the run message is updated to reflect the choice, and the user receives an ephemeral confirmation message.\
![Pressed Tank role](/readme_pictures/press_tank.jpg)\
![Button response](/readme_pictures/button_response.jpg)

If a user presses any button they already have signed up for, they are removed from the role, and receive an empheral confirmation message. If a user that is signed as any role, presses any *other* role button, they will be swapped to that role, and, again, receive a confirmation message.

You cannot sign up as filled roles.

If they key as created with a role completely filled, the associated button will be greyed out, and cannot be pressed. (Note the DPS button)\
![Reserved roles](/readme_pictures/reserved_roles.jpg)

### Cancel & Lock run/Un-lock run
The following 2 buttons will cancel a run, and lock a run respectively. 

The `CANCEL` button will delete the run message completely.\
![Cancelled run](/readme_pictures/run_cancelled.jpg)

The `LOCK RUN` button will "lock" the run, disabling the role buttons, and send a message pinging all signed up users.\
![Locked run](/readme_pictures/run_locked.jpg)

Once a run has been locked, the `LOCK RUN` button will change into `UN-LOCK`. This button allows the run starter to un-lock the run, allowing users to interact with the role buttons again. 

## Roles
The /roles command allows any user to enable and disable /key role pings.\
![Roles](/readme_pictures/roles.jpg)

The response message has three buttons, one for each role. Pressing any of them will either enable or disable role pings, depending on whether the user has them "turned" on or off already. An ephemeral confirmation message is sent to the user.\
![Disabled tank](/readme_pictures/disabled_tank.jpg)