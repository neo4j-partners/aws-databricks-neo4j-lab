---
marp: true
theme: default
paginate: true
---

<style>
section {
  --marp-auto-scaling-code: false;
}

li {
  opacity: 1 !important;
  animation: none !important;
  visibility: visible !important;
}

/* Disable all fragment animations */
.marp-fragment {
  opacity: 1 !important;
  visibility: visible !important;
}

ul > li,
ol > li {
  opacity: 1 !important;
}
</style>


# Traditional RAG: Chunking and Vector Search

---

## Why RAG Was Adopted

Remember the LLM limitations we discussed:
- **Hallucination** - Generates confident but wrong information
- **Knowledge cutoff** - No access to your private data
- **Relationship blindness** - Can't connect information

**The insight:** If we could provide LLMs with relevant context, we could address these limitations.

This led to **Retrieval-Augmented Generation (RAG)**.

---

## The Power of Context

Providing context in prompts dramatically improves LLM responses.

**When you include relevant information, the model can:**
- Generate accurate summaries grounded in actual documents
- Answer questions about your specific data
- Reduce hallucination by having facts to reference

**RAG automates this:** Instead of manually adding context, retrieve it automatically based on the user's question.

---

## How Traditional RAG Works

Traditional RAG follows a simple pattern:

1. **Index documents**: Break documents into chunks and create embeddings
2. **Receive query**: User asks a question
3. **Retrieve context**: Find chunks with embeddings similar to the query
4. **Generate response**: Pass retrieved chunks to LLM as context

Let's understand each component: chunking, embeddings, and vector search.

---

![bg contain](../../images/embeddings_visual.jpg)

---

## The Smart Librarian Analogy

Think of embeddings like having a **really smart librarian** who has read every book in the library.

**Traditional catalog (keywords):**
- Books organized by title, author, subject
- Search for "dogs" only finds books with "dogs" in the title/subject
- Miss books about "canines," "puppies," or "pets"

**Smart librarian (embeddings):**
- Understands what each book is *about*
- "I want something about loyal companions" → finds dog books, even without the word "dog"
- Organizes by meaning, not just labels

---

![bg contain](../../images/beyond_keywords.jpg)

---

## The RAG Retrieval Flow

```
User Question
     ↓
Create embedding of question
     ↓
Compare to all chunk embeddings
     ↓
Return top K most similar chunks
     ↓
Send chunks + question to LLM
     ↓
LLM generates answer using chunks as context
```

---

## Traditional RAG: What It Enables

**Works well for:**
- "What does this document say about X?"
- Finding relevant passages by topic
- Answering questions within a single document

**The foundation of modern AI assistants**, but as we'll see, it has important limitations when dealing with connected information.

---

## Summary

In this lesson, you learned:

- **RAG** provides relevant context to LLMs automatically
- **Embeddings** encode text meaning as vectors—similar meanings produce similar vectors
- **Semantic search** finds relevant content by meaning, not keywords
- **Traditional RAG** combines these to ground LLM responses in real data

**Next:** Understanding the limits of traditional RAG and how GraphRAG addresses them.
