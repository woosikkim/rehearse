I wrote `/app/meeting_scheduled.ics` with the "Team Planning Meeting" on Wednesday, January 17, 2024, 11:00–12:00 UTC. It lists alice@example.com, bob@example.com and carol@example.com as attendees.

I worked out the slot by hand from the three calendars. I didn't write a script, and I haven't run a validator on the output file or read it back.

Monday and Tuesday have no common 60-minute gap, and on Wednesday Alice is busy 10–11, so 11:00 is the earliest start. It satisfies every constraint, including Carol's Monday preference and Alice's morning preference. The three input calendars are untouched.

I also logged the steps in `.rehearsal/REHEARSAL.md`.