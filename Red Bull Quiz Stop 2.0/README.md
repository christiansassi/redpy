# Table of Contents

- [Introduction](#introduction)
- [How? (For the Most Curious)](#how-for-the-most-curious)
  - [Step 1: Observing the Traffic](#step-1-observing-the-traffic)
  - [Step 2: Understanding the Encryption](#step-2-understanding-the-encryption)
  - [Step 3: Inspecting Decrypted Requests](#step-3-inspecting-decrypted-requests)
  - [Step 4: Understanding the Answers](#step-4-understanding-the-answers)
  - [Step 5: Maximizing the Score](#step-5-maximizing-the-score)
  - [Final Strategy](#final-strategy)
- [Installation and Configuration](#installation-and-configuration)
  - [mitmproxy](#mitmproxy)
  - [Python](#python)
- [Usage](#usage)
- [Demo](#demo)
- [Known Limitations](#known-limitations)

# Introduction

This contest involved answering six questions correctly within the given time limit. Players also had access to a powerup that could boost their chances of winning or increase their final score.

You can try it yourself by visiting [Red Bull Quiz Stop 2.0](https://www.redbull.com/it-it/projects/red-bull-quiz-stop-motorsport).

I created this tool as a simple MITM (man-in-the-middle) proxy. It intercepts the requests the client sends to the server while the user is playing, modifies them (as explained in the *[How? (For the Most Curious)](#how-for-the-most-curious)* section), and achieves the highest possible score.  

There are many ways this could be implemented, but I chose a MITM approach for simplicity. If a user wants to save their result, they still need to log in and submit the form, so this method avoids having to implement login and form submission logic, which is outside the scope of this project.

# How? (For the Most Curious)

## Step 1: Observing the Traffic

I first played the game and captured all requests and responses exchanged with the server. I wanted to know whether submitting an answer actually triggered a request beyond analytics. To my surprise, it did. In an older contest ([Red Bull Giro Veloce](https://www.redbull.com/it-it/projects/red-bull-giro-veloce)), everything was handled client-side. Now, requests were sent to the server and the payloads were encrypted.

## Step 2: Understanding the Encryption

At this point, I needed to figure out how the requests were encrypted and whether decrypting them would help. Using the browser's developer tools, I inspected the call stack for these requests and traced them to [`bundle.js`](https://p-p.redbull.com/rb-global-muiz-stop-20-72-prod/bundle.js). The file was mostly readable except for a section that had clearly been obfuscated, so I focused my efforts there. After several attempts at deobfuscation, I gained valuable insights about the obfuscated code, including the encryption function.

```js
function Mr(t) {
    var e = Pr,
        r = arguments[e(347)] > 1 && void 0 !== arguments[1] ? arguments[1] : null,
        n = Math[e(266)](1e8 * Math[e(414)]() + (new Date)[e(265)]() / 3),
        i = Or.A.PK + Math[e(270)](n / 2);

    return Dr({
        t: n,
        d: Lr()[e(285)].encrypt(JSON.stringify(t), i)[e(397)]()
    }, r && {
        z: r
    })
}
```

The function used AES-256-CBC with an encryption key in the format `932748hfidufdwofuyfiuys8ryf7r8XXXXXXXXXXXX`, where `932748hfidufdwofuyfiuys8ryf7r8` is the base key and `XXXXXXXXXXXX` is a twelve-digit number generated partly from the datetime and partly at random.

Instead of manually searching for the base key in the code, I used a tool to replace `bundle.js` when the webpage requested it from the server. My modified version simply printed all the keys whenever something was encrypted. This saved me a lot of headaches.

## Step 3: Inspecting Decrypted Requests

With decryption working, I found two key fields in the client payloads:

- `gameid`: identifies the current game session  
- `actions`: lists all actions performed by the player  

At this point, I knew I had to modify the payload to submit my own answers. The remaining question was how to determine the correct answer.

## Step 4: Understanding the Answers

The game has two types of challenges:  

- **Questions**: multiple choice questions. The server expects `"value": 0` in the payload for a correct answer.  
- **Pairs**: you must reorganize items based on images. The server expects the submitted array to be in ascending order `"value": [0, 1, 2, 3, 4, 5]`.  

This was enough to always submit the correct answer.

## Step 5: Maximizing the Score

Submitting correct answers was not enough. I wanted the highest possible score. After some testing, I discovered that the score is determined by two other factors: **Powerup** (obviously) and most importantly **Speed of Answer**.

- **Powerups**: there are three powerups: `time`, `double`, and `remove`. `time` and `remove` are irrelevant since we control submissions, but `double` is very valuable as it doubles the score. Interestingly, using it on questions gave me more points than using it on pairs. Keep in mind that powerups can only be used once per game. Using them multiple times causes a server error.

- **Speed**: the speed is derived from the `frame` field in the `actions` array, which tracks when each interaction occurred. Fewer and faster actions give more points. By minimizing actions to just two (select and submit), I could simulate a very fast player. However, frames that were too small (like `0` or `1`) were rejected by the server, likely as anti-cheat protection. After a quick binary search, I found the valid frame values: for questions, select at `11` and submit at `15`; for pairs, select at `1` and submit at `60`. The difference makes sense since pairs take more time to complete physically.

## Final Strategy

Here is the process I used to achieve a near-perfect score:  

1. Find a game that gives you the double powerup (this may take a few tries).  
2. Submit answers programmatically using the discovered encryption and decryption method. 
    - Set the frames to the optimal values (`11` and `15` for questions, `1` and `60` for pairs). 
    - Use the powerup only once and apply it to a question to maximize your score.  

Following this strategy, I reached a final score of **67.833**.

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

1. Run the script with `python main.py` and wait until you see `[XXXX-XX-XX XX:XX:XX] Ready! https://www.redbull.com/it-it/projects/red-bull-quiz-stop-motorsport`.
2. Open your browser **with the proxy activated and pointing to mitmproxy**.
3. Navigate to [Red Bull Quiz Stop 2.0](https://www.redbull.com/it-it/projects/red-bull-quiz-stop-motorsport).
4. Start a new game and play freely. Your answers do not matter because the script will intercept and submit the correct payload automatically.
5. Once finished, save the result and complete the form.

> [!TIP]
> It is recommended to do everything while logged in so that the submitted form is linked to your account. If you plan to do this, log in before step 4.

⚠️ **To ensure a smooth experience, follow these recommendations:**

- Once the script is executed, it will be valid for only one game session. If you want to play multiple sessions, restart the script. You can keep the browser open but avoid browsing other websites, as the proxy will be disabled and you will not be able to connect.
- If you close the game window by clicking the x, the current session will be invalidated. You must restart the script to obtain a new valid game session.

# Demo

<div align="center">
    <p>
        <img width="100%" src="assets/demo.gif"/>
        <i>Demo</i>
    </p>
</div>

# Known Limitations

This tool currently has two main limitations:

- **Speed**: as explained earlier, frame values are set to the lowest possible values that are still accepted by the server as valid. While this maximizes the score, a human reviewer could easily notice that the actions were performed unnaturally fast. You can modify the source code to experiment with more "human-like" frame values, but make sure they are realistic and reproducible by an actual player.

- **Pairs Answers**: at the moment, the script simulates a single move that results in the correct final order, then submits the solution. This works but is not realistic for puzzles that would normally require multiple moves. Again, a manual review could detect this discrepancy. You could improve this by modifying the code to calculate the minimum number of moves needed to solve the puzzle and submit them sequentially, better simulating a real player's behavior.
