# Phase 1: Model Selection

## Why Google Gemini Pro?

I picked Google Gemini Pro after comparing it with the other major options. The decision came down to three things: it's completely free, the quality is good enough for what we need, and I could get it running in under five minutes.

---

## Cost Breakdown

**Gemini Pro is free.** No credit card, no billing surprises, no "free tier that runs out after two weeks." You get:
- 60 requests per minute
- 1,500 requests per day
- 1 million requests per month

For comparison:
- GPT-3.5-Turbo would cost around $30/month for similar volume
- GPT-4 would run closer to $450/month
- Claude needs a credit card even though you get $5 of credit
- Llama requires your own servers and GPUs

For an academic project or early MVP, spending zero dollars matters. You can validate the concept without touching the budget.

---

## Quality Check

I tested Gemini on the actual use cases: order status queries and return policy questions. It handled them fine.

**What it does well:**
- Reads JSON data accurately
- Doesn't make things up when the data is clear
- Writes natural-sounding responses
- Adjusts tone appropriately (more empathetic for delays, straightforward for confirmations)

**Where it struggles:**
- Very long conversations (100+ messages) start getting confused
- Needs clear instructions or it goes off-script
- Sometimes tries to be too helpful and overexplains

But for "tell me where my package is" and "can I return this toothbrush," it works. The difference between Gemini and GPT-4 on these specific tasks isn't worth spending 30x more money.

---

## The Speed Problem

Right now, EcoMarket's support team takes about 24 hours to respond. That's not great. With AI handling the straightforward queries, response time drops to around 2 seconds. That's a 12,000x improvement, which sounds made up but isn't.

The catch: AI can't handle everything. Maybe 20% of queries need actual human judgment—someone's upset, the situation is weird, the policy doesn't quite fit. Those still go to people. But the other 80% ("where's my order," "what's your return policy") get answered immediately.

---

## How It Would Work

The basic setup is simple:

```
Customer asks a question
     ↓
System decides: is this straightforward or complicated?
     ↓                           ↓
Simple query              Complex query
     ↓                           ↓
Gemini answers           Human agent handles it
with database info
     ↓
Response back to customer
```

**For the AI part:**
- Connect to the orders database
- Load return policies
- Give Gemini clear instructions on tone and format
- Send the query

**For the human escalation:**
- Pass along the full conversation so far
- Flag what made it complicated
- Let the agent take over

---

## Why Not the Others?

**GPT-4:** Expensive. Really good, but overkill for "where's my package." If you're doing complex reasoning or multi-step analysis, maybe worth it. For customer service queries, no.

**GPT-3.5:** Costs money and needs a credit card. Quality is comparable to Gemini. The only reason to use it is if you already have OpenAI infrastructure set up.

**Claude:** Also needs payment setup. The 100K+ token context window is impressive, but we're not processing entire novels here—we're looking up order statuses.

**Llama (running it yourself):** Gives you full control and no per-query costs after setup. But you need servers, GPUs, monitoring, scaling logic. That's a project in itself. Makes sense for companies with strict data requirements or massive volume, not for a pilot.

---

## Quick Comparison

| What matters | Gemini | GPT-3.5 | GPT-4 | Claude | Llama |
|-------------|--------|---------|-------|--------|-------|
| Cost | Free | ~$30/mo | ~$450/mo | Paid | Infrastructure |
| Setup time | 5 min | 20 min | 20 min | 20 min | Days |
| Needs payment | No | Yes | Yes | Yes | No (but servers) |
| Quality for this | Good | Good | Excellent | Good | Decent |
| Response speed | 1-2s | 2-3s | 4-6s | 2-3s | <1s |

---

## What Success Looks Like

**Performance:**
- Get the right answer >95% of the time
- Don't make things up (<1% hallucination rate)
- Respond in under 3 seconds

**Business:**
- Customers happy (>85% satisfaction)
- Resolve most queries without escalation (>80%)
- Escalate 15-25% to humans (the actually complex stuff)

**Cost:**
- Stay in the free tier
- Spend $0 per query
- Save more than we would by just hiring another support person

---

## The Real Reason

Gemini works for this use case and costs nothing. If it stops working, we can switch models with maybe 2 hours of code changes. The prompts are portable. The risk is low.

I'm not saying it's the best model on the planet. I'm saying it's good enough for order status and return policies, and I can deploy it today without filling out a procurement form.