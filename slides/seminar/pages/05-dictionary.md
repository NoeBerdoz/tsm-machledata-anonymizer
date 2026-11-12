---
part: 2
eyebrow: The teacher
clicks: 3
source: 'Counted from the published weights, and on 103,718 OpenPII-1M texts in our four languages. Estimates in the appendix.'
---

# Most of the teacher is *a dictionary*

The dictionary turns each token, a word or a piece of one, into learned numbers: parameters.

<TeacherSize />

<style>
/* the lede defines token and parameter in one line, so it may use the full width */
h1 + p {
  max-width: none;
}
</style>

<!--
Target time 0:35. Speaker: to assign.

The teacher has 307 million parameters. Most of them, 63 percent, are its dictionary.
[click] This dictionary has tokens for many languages.
[click] Our model targets Switzerland. We need only French, German, Italian and English. They use under a third of the tokens.
[click] If time allows, we drop the other tokens. The model would fall to about 174 million parameters.

If asked: the four slices are only a picture. Many tokens serve several languages, and 77,347 counts each token once.
-->
