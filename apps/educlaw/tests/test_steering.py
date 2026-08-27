from educlaw.agent.steering import GateDecision, SteeringQueue, apply_gate, decide_gate


def test_fifo_order() -> None:
    queue = SteeringQueue()
    queue.push("first")
    queue.push("second")
    assert queue.pop().text == "first"
    assert queue.pop().text == "second"
    assert queue.pop() is None


def test_abort_decision() -> None:
    from educlaw.agent.steering import SteeringMessage

    assert decide_gate(SteeringMessage("/abort"), running=True) is GateDecision.ABORT
    assert decide_gate(SteeringMessage("stop", kind="abort"), running=True) is GateDecision.ABORT


def test_steer_now_for_short_instruction() -> None:
    from educlaw.agent.steering import SteeringMessage

    assert decide_gate(SteeringMessage("use blue instead"), running=True) is GateDecision.STEER_NOW


def test_answer_later_for_long_or_question() -> None:
    from educlaw.agent.steering import SteeringMessage

    assert decide_gate(SteeringMessage("what is the current scene?"), running=True) is GateDecision.ANSWER_LATER
    long_text = "please " + ("continue " * 40)
    assert decide_gate(SteeringMessage(long_text), running=True) is GateDecision.ANSWER_LATER


def test_apply_gate_requeues_answer_later() -> None:
    queue = SteeringQueue()
    queue.push("use red")
    queue.push("what color did we pick?")
    decision, steers, aborted = apply_gate(queue, running=True)
    assert not aborted
    assert decision is GateDecision.STEER_NOW
    assert steers == ["use red"]
    leftover = queue.drain()
    assert [item.text for item in leftover] == ["what color did we pick?"]


def test_apply_gate_abort_keeps_remaining() -> None:
    queue = SteeringQueue()
    queue.push("nudge")
    queue.push("/abort")
    queue.push("after abort")
    decision, steers, aborted = apply_gate(queue, running=True)
    assert aborted
    assert decision is GateDecision.ABORT
    assert steers == ["nudge"]
    leftover = queue.drain()
    assert [item.text for item in leftover] == ["after abort"]
