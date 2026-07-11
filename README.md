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
```

## proxies

discord blocks datacenter ips (you'll get a bunch of 403s), so for bigger runs you want
residential proxies. drop them in a `proxies.txt` next to where you run it and they get
picked up automatically. one per line:

```
host:port
host:port:user:pass
socks5://user:pass@host:port
```

see `proxies.txt.example`. without proxies it still works, just slower and you'll hit
rate limits sooner.

## disclaimer

this is for checking if a name you want is free. be nice to discord's api, keep your
rate reasonable, and follow their terms. don't be weird with it.

## license

MIT
