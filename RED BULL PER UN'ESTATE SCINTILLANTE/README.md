# Table of Contents

- [Introduction](#introduction)
- [How? (For the Most Curious)](#how-for-the-most-curious)
  - [Step 1: Observing the Traffic](#step-1-observing-the-traffic)
  - [Step 2: Win a Game](#step-2-win-a-game)
  - [Step 3: Win a Game by Hijacking It](#step-3-win-a-game-by-hijacking-it)
  - [Step 4: Maximizing the Score](#step-4-maximizing-the-score)
  - [Final Strategy](#final-strategy)
- [Installation and Configuration](#installation-and-configuration)
  - [mitmproxy](#mitmproxy)
  - [Python](#python)
- [Usage](#usage)
- [Demo](#demo)

# Introduction

This contest involved moving the cursor inside a panoramic scenario [scenario.webp](assets/scenario.webp) and find all the cans.

You can try it yourself by visiting [RED BULL PER UN'ESTATE SCINTILLANTE](https://www.redbull.com/it-it/projects/estatescintillante).

I created this script as a simple js script to help you finish the game without wasting to much time and then a python script to intercept your result (whatever it is, the important thing is to finish the game) and replace it with a perfect game (as explained in the *[How? (For the Most Curious)](#how-for-the-most-curious)* section).

There are many ways this could be implemented, but I chose this approach for simplicity. Of course you can create an automated browser instance that do everything for you, however, in this challenge I think this is not indispensable.

# How? (For the Most Curious)

## Step 1: Observing the Traffic

I first played the game and captured all the requests and responses exchanged with the server. This time, on a failed game, nothing was submitted at all.

## Step 2: Win a Game

At this point, I needed to win a game first. The obvious question followed: how can a perfect game be played? By inspecting the traffic, I noticed that the scene and the cans are always the same. I asked an AI to write a very simple script to interact with the spherical scene (I did not want to spend time understanding its geometry).

I added a delay between clicks and started experimenting with it. With a value below 25ms the game froze (the engine physically did not have time to process the inputs). With a value below 335ms the game ran quickly, but the server rejected the submission (I assumed, as with the previous Red Bull contest, that the server runs some form of human/bot verification). 335ms turned out to be the sweet spot. However, after running the script several times, I noticed that the script itself introduced small delays, so the score was not always identical (small variations, but still inefficiencies).

## Step 3: Win a Game by Hijacking It

The only way to remove these inefficiencies was to inspect the submitted payload after a winning game. Once again, the payload was obfuscated. The body of each request is a base64-encoded ciphertext. The ciphertext is produced by XOR-ing every byte of the encoded payload with a single-byte key. The payload itself is MessagePack for the game-submit endpoint and JSON for every other endpoint. The key is derived by collapsing a longer key string into one byte: the character codes are XOR-folded together starting from zero. For the game-submit endpoint the key string is the gameId, which the client also sends in the clear in a custom request header so the server can derive the same byte. For every other endpoint the key string is a constant baked into the application bundle.

## Step 4: Maximizing the Score

Deobfuscating the body of a winning game was enough, since it could be reused later for new games. The body essentially contains all the actions performed by the user, but the most important value is the total time taken to complete all the moves. I tried different offsets between moves, but in the end it turned out that the server only checks the final value (the last move). If it is lower than 211, the server invalidates the game session (treating it as non-human behavior). So the sweet spot was 211 (211 / 60 = 3.517s).

## Final Strategy

By using main.js to play through and win a game, and the Python script to inject a perfect-game payload, I reached a final score of **71.483**.

If you manage to score even higher, I would love to know how you did it! ![](assets/jawdrop.gif)

# Installation and Configuration

First, clone this repository by running `git clone https://github.com/christiansassi/redpy`

## <img src="https://www.mitmproxy.org/favicon.ico" width="20" style="position: relative; top: 2px; margin-right: 8px;" /> mitmproxy

1. Download and install mitmproxy from [here](https://www.mitmproxy.org/).
2. Install the mitmproxy certificate:
    1. Start mitmproxy by running `mitmdump` in the terminal.
    2. Set the proxy of your device to `http://127.0.0.1:8080` (or whatever mitmproxy indicates). Alternatively, and this is strongly recommended, since everything in this project relies on the browser, you can start your browser with the appropriate proxy flags. For Chrome, for example, the flag is `--proxy-server="http://127.0.0.1:8080"`.
    3. Open [mitm.it](http://mitm.it/) and download the certificate.
    4. Install the certificate you just downloaded.

## <img src="https://www.python.org/static/favicon.ico" width="20" style="position: relative; top: 2px; margin-right: 8px;" /> Python

Install the required packages by running `pip install -r requirements.txt`.

# Usage

1. Run the script with `python main.py` and wait until you see `[XXXX-XX-XX XX:XX:XX] Ready! https://www.redbull.com/it-it/projects/estatescintillante`.
2. Open your browser **with the proxy activated and pointing to mitmproxy**.
3. Navigate to [RED BULL PER UN'ESTATE SCINTILLANTE](https://www.redbull.com/it-it/projects/estatescintillante).
4. Inject `main.js` (the DevTools console works fine).
5. Start a new game and let the JS script play it for you.
6. Once finished, save the result and complete the form.

# Demo

<div align="center">
    <p>
        <img width="100%" src="assets/demo.gif"/>
        <i>Demo</i>
    </p>
</div>
