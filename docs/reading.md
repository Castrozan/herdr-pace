# Reading with Herdr Pace

The reader opens paused. Space starts your chosen countdown, then shows the first word for its full reading interval. Resuming, restarting, and replaying use the same countdown. Space also cancels a countdown and pauses.

Speed ranges from 50 to 2,000 words per minute. Countdown ranges from 0 to 10 seconds; 0 starts immediately. Both preferences are saved when you close the reader.

Changing speed during a countdown leaves its next tick alone. Adjusting an active countdown preserves elapsed seconds. Changing the countdown while reading applies to your next start.

## Pauses that follow your pace

| Boundary                                      | Cue | Duration                                 | At 400 WPM | At 800 WPM |
| --------------------------------------------- | --- | ---------------------------------------- | ---------- | ---------- |
| Paragraph, heading, list item                 | ¶   | Four word intervals: `240 / WPM` seconds | 0.6 s      | 0.3 s      |
| Explicit Markdown break, code line, table row | ↵   | Two word intervals: `120 / WPM` seconds  | 0.3 s      | 0.15 s     |

Ordinary wrapped lines flow continuously. Cues do not count as words. Changing speed during a cue preserves the time already elapsed; the next word still receives its full interval. Pausing during a cue and resuming runs your countdown, then shows the next word. Words ending in punctuation stay visible for 2.5 word intervals.

## A quiet reading pane

Only the central word, countdown, or break cue changes automatically. The footer and total word count stay fixed. Changing a setting or resizing the pane updates the surrounding layout without changing the controls' wording.

Large text occupies three terminal rows. The focus letter stays centered, long words fit inside the pane, and Unicode shaping includes CJK and emoji fallback. Long identifiers continue across successive words without losing text.

Pace asks the terminal for its foreground and ANSI red colors before drawing. If both colors arrive within 250 milliseconds, it uses large text and checks colors once per second. Otherwise it stays with ordinary terminal text for that opening. A late response never changes the font size. Font preparation adds to opening time.

An empty reader means no completed reply has been captured for that pane and server. Check that hooks are installed, restart the AI session, and wait for a completed reply before opening again.
