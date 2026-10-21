"""The gates on the failure records, the wait answers and the irreversible step, in one place, with two callers:
bin/rehearse refuses before the command runs, so the agent sees why at once, and the hook refuses the record past
the command, so a faked result line changes nothing. Each function returns why the record is refused, or None."""
import log as L
import state as S

REVIEWER = "rehearse:reviewer"


def steps(arg):
    return [x.strip() for x in (arg or "").split(",") if x.strip()]


def missing_steps(s, cited, what="step"):
    logged = {r["step"] for r in L.records(s["run_folder"]) if "step" in r}
    missing = [x for x in cited or [] if x not in logged]
    if not cited or missing:
        return "every %s must be in the log: %s" % (what, ", ".join(missing) or "none given")
    return None


def no_websearch(s, reason):
    """A reason for citing no WebSearch is accepted only when the job was activated with WebSearch declared
    unavailable (the websearch setting; REHEARSE_WEBSEARCH=0), and never when the log shows one was made."""
    if not reason:
        return None
    if s.get("websearch", True):
        return ("--no-websearch is refused: WebSearch is available in this environment (the websearch setting; "
                "REHEARSE_WEBSEARCH=0 declares it unavailable); cite a WebSearch step")
    web = L.search_steps(s["run_folder"], web=True)
    if web:
        return "--no-websearch is refused: WebSearch was used in this run (%s); cite a WebSearch step" % ", ".join(sorted(web))
    return None


def tried(s, cited, reason):
    return missing_steps(s, cited) or no_websearch(s, reason)


def review(s, searched, candidates, reason, by=None, hook=False):
    """by: the recording agent's type (None: the manager), known to the hook only."""
    if hook and len(s.get("stages") or []) == 1 and by != REVIEWER:  # the strongest fresh eyes: the manager did the work
        return "in a one-stage job only rehearse:reviewer records the review: start it"
    if hook and by in {x.get("by") for x in s.get("tried") or []}:
        return "a review needs fresh eyes: the agent that made the tried records may not review them"
    searches = L.search_steps(s["run_folder"])
    not_search = [x for x in searched or [] if x not in searches]
    if not searched or not_search:
        return ("every --searched step must be a logged search (a WebSearch or WebFetch call, or rehearse fetch): %s"
                % (", ".join(not_search) or "none given"))
    if not S.cites_search({"searched": searched, "no_websearch": reason}, L.search_steps(s["run_folder"], web=True)):
        return ("at least one --searched step must be a logged WebSearch (methods are found by search; a fetch alone "
                "is not a search); only with the websearch setting off may --no-websearch give the reason instead")
    why = no_websearch(s, reason)
    if why:
        return why
    names = S.tried_names(s)
    for c in candidates or []:
        if str(c.get("name", "")).strip().lower() in names:
            return "candidate %r names a route already tried; a candidate is something new" % c.get("name")
    return None


def failed(s):
    """Gate two: only after a review whose every candidate is tried or dropped, with a tried route citing a search."""
    if s["phase"] not in ("look", "build"):
        return "rehearse failed is recorded in look or build; the job is in %s" % s["phase"]
    if not s.get("reviews"):
        return "no review is recorded for %s: review the log first (rehearse review)" % S.label(s)
    if S.untried(s):
        return "candidates of the latest review are neither tried nor dropped: %s" % ", ".join(
            c["name"] for c in S.untried(s))
    web = L.search_steps(s["run_folder"], web=True)
    if not any(S.cites_search(x, web) for x in s.get("tried") or []):
        return ("failed is recorded only after at least one route was tried, recorded, and cites a logged WebSearch "
                "(or a recorded --no-websearch reason)")
    return None


def wait(s, answer, says, confirmed):
    """The 3.0.1 and 3.2.0 guards: stop here from any question; the user must have spoken since the question arose;
    --says is their words, word for word; correct has failing checks to change; change needs the second yes."""
    waiting = s["phase"] == "wait"
    if answer != "stop here" and not waiting:
        return "rehearse wait is accepted while the stage waits; the job is in %s" % s["phase"]
    since = S.question_since(s)
    if not s.get("user_answer_at") or s["user_answer_at"] < since:
        return ("no answer from the user is recorded since %s: ask them (a prompt, or AskUserQuestion), then record "
                "what they chose" % ("the wait began" if waiting else "the last worker stopped"))
    if answer in ("correct", "resume") and not (says or "").strip():
        return "give the user's words with --says: %s; they are recorded with the decision" % (
            "which checks are wrong and what is right (correct keeps the work and changes only the failing checks)"
            if answer == "correct" else "what they gave or decided")
    if answer in ("correct", "resume") and not S.said(s, says, since):
        return "--says must be the user's words, word for word, from an answer recorded since the wait began; not a paraphrase"
    if answer == "correct" and not S.failing(s):
        return "correct has nothing to apply: no failing check is recorded for %s (no run of the ending failed)" % S.label(s)
    if answer == "change" and not confirmed:
        return ("change redoes %s from the look: a look worker, the ending registered and confirmed again, then the "
                "build and the director. Put that to the user as one yes-or-no question, and run this again with "
                "--confirmed only after an explicit yes" % S.label(s))
    return None


def wrong(s, check, evidence):
    if s["phase"] not in ("look", "build"):
        return "rehearse wrong is recorded in look or build; the job is in %s" % s["phase"]
    why = missing_steps(s, evidence, "evidence step")
    if why:
        return why
    bad = [r.get("requirement") for r in S.failing(s)]
    if check not in bad:
        return "wrong names a check the last run failed: %s" % (", ".join(bad) or "none recorded")
    return None


def irreversible(s):
    ir = s.get("irreversible")
    if not ir or not ir.get("ok") or s["phase"] != "done.passed":
        return "rehearse irreversible runs only the step the user OK'd, after the final pass (%s; phase %s)" % (
            S.irreversible_text(s), s["phase"])
    if ir.get("ran"):
        return "the irreversible step already ran once (rc %s); it never runs twice" % ir["ran"].get("rc")
    return None
