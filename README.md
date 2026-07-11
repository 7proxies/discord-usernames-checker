# discord username checker

find the short discord usernames that are still free. 3, 4 and 5 letter names, or your own patterns.

![python](https://img.shields.io/badge/python-3.9+-blue)
![license](https://img.shields.io/badge/license-MIT-green)

```
     _              _
 __ | |_   ___  __ | |__ ___  _ _
/ _|| ' \ / -_)/ _|| / // -_)| '_|
\__||_||_|\___|\__||_\_\\___||_|
```

discord switched to unique @usernames (pomelo), so all the good short ones got taken fast. this checks which are still open by asking discord's own signup endpoint, so the answer is real, not a guess.

## install

```bash
pip install discord-username-checker
```

or just run it without installing:

```bash
pipx run discord-username-checker
```

then start it:

```bash
dusc
```

## what it does

pick from the menu:

- **3 / 4 / 5 letter names** - checks every combo
- **custom pattern** - build your own with the highlighter
- **check from a file** - give it a list of names and it checks those
- **settings** - proxies, workers, output file

free names get printed as they're found and saved to `available.txt`.

## custom patterns

type a word, then walk over each letter and set what it can be:

| key | means | what it can be |
|-----|-------|----------------|
| `f` | fixed | the letter you typed |
| `l` | letter | a-z |
| `d` | digit | 0-9 |
| `n` | letter or digit | a-z 0-9 |
| `u` | anything | a-z 0-9 `.` `_` |

move with the arrow keys, change a spot with up/down or space, hit enter to run.

so if you type `cool` and mark the two `o`s as letters you get `c??l` and it checks
`caal, cabl, cacl ...` all the way through. the discord rules are built in, so it never
tries a name with two dots in a row or one that starts with a dot.

there's also a flag version if you want to script it:

```bash
dusc --pattern "co??"     # ? letter, # digit, * letter/digit, % anything
dusc --three              # all 3 letter names
dusc --four --workers 20
dusc --file names.txt     # check a list from a file
```

## check from a file

got your own list? put one name per line and point the tool at it:

```bash
dusc --file names.txt
```

bad ones (too short, two dots, starts with a dot, uppercase) get cleaned out and
duplicates are dropped, then it checks the rest.

## how fast / rate limits

discord doesn't give a nice number for this endpoint, it's a hidden per-ip bucket. if you
hammer it you get thrown in a cooldown that can be 10-15 minutes long. if you go slow it
holds up fine.

so the tool paces itself: it spaces requests per ip (`--gap`, default 0.6s ≈ ~1.5/sec) and
if it does get rate limited it just waits the cooldown out and retries the name instead of
dropping it. nothing gets lost, it only goes slower.

rough idea of what you get from **one ip** (no proxies):

- all 3 letter names (17,576) - easy, one evening
- a night of running - low tens of thousands, ish
- all 4 letter names (456,976) - not happening on one ip, use proxies

want more? add proxies, every extra ip is another lane running in parallel. bump `--gap`
down a bit if your proxies are good, up if you're getting rate limited.

## proxies

each proxy is its own ip with its own limit, so more proxies = more throughput. drop them
in a `proxies.txt` next to where you run it and they get picked up automatically, one per
line:

```
host:port
host:port:user:pass
socks5://user:pass@host:port
```

see `proxies.txt.example`. residential proxies are best - some datacenter ips just get a
flat 403 from discord.

**on a vpn (mullvad etc)?** just run it while connected, all traffic goes through the vpn
ip. when it hits a cooldown, switch to another server for a fresh ip and it keeps going.
one ip at a time so it's not fast, but it's free and it's only you.

without any of that it still works, just slower and you'll hit cooldowns sooner.

## disclaimer

this is for checking if a name you want is free. be nice to discord's api, keep your
rate reasonable, and follow their terms. don't be weird with it.

## license

MIT
