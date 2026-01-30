# Recording Script: Hierarchical RAG Pipeline Walkthrough

**For OBS Recording - Google Colab Notebook Demonstration**

Use this script while recording yourself explaining the notebook. Each section corresponds to a cell or group of cells.

---

## Pre-Recording Checklist

Before you start recording:
- [ ] Open Google Colab with the notebook loaded
- [ ] Ensure you have A100 GPU runtime selected
- [ ] Have your Google Drive with PDFs ready
- [ ] Add `GROQ_API_KEY` to Colab secrets
- [ ] Test OBS audio/video

---

## INTRODUCTION (Before Cell 0)

**Say:**
> "Welcome! Today I'll walk you through building a Retrieval-Augmented Generation system, or RAG system, for academic literature review. This notebook is optimized for Google Colab with an A100 GPU, which gives us 50 to 100 times faster processing compared to running on a CPU.
>
> The goal is to create a searchable knowledge base from 85 academic PDFs on German regional economic transitions, and then use AI to answer questions about them with proper citations."

---

## CELL 0: Title & Overview (Markdown)

**What it shows:** Introduction, setup checklist, performance comparison table

**Say:**
> "This first cell gives us an overview of what we're building. You can see the setup checklist - we need to enable the A100 GPU, upload our PDFs to Google Drive, and run cells in order.
>
> The performance table shows why we're using Colab Pro with A100. Processing 2 PDFs takes about 30 seconds on GPU versus 5-10 minutes on CPU. For all 85 PDFs, we're looking at 15-20 minutes on GPU versus 2-3 hours on CPU. That's a massive speedup."

---

## CELL 1-2: Mount Google Drive

**What it does:** Mounts Google Drive to access your PDFs

**Say:**
> "Step 1 mounts our Google Drive. This is essential because our PDFs are stored there. When you run this cell, you'll get a popup asking you to authorize access to your Google account."

**Run cell 2, then say:**
> "Once authorized, we can access all our files at the path `/content/drive/MyDrive/`."

---

## CELL 3: Check GPU Availability

**What it does:** Verifies A100 GPU is available and shows memory

**Say:**
> "This cell checks if our GPU is properly configured. We're using PyTorch's CUDA detection to verify we have the A100."

**After running:**
> "You can see it detected our A100 GPU with 40 gigabytes of memory. If you see 'No GPU found', go to Runtime, Change runtime type, and select A100 GPU."

---

## CELL 4-5: Install Dependencies

**What it does:** Installs all required Python packages

**Say:**
> "Step 2 installs all our dependencies. We're using:
> - **LlamaIndex** - the main RAG framework
> - **HuggingFace Embeddings** - for converting text to vectors
> - **ChromaDB** - our vector database for storing embeddings
> - **PyMuPDF** - for extracting text from PDFs
> - **Pandas** - for data processing
>
> The `%%capture` magic command suppresses the output to keep the notebook clean."

---

## CELL 6-7: Setup Paths

**What it does:** Defines folder paths for PDFs and data files

**Say:**
> "Step 3 is critical - we set up our paths. The `BASE_PATH` variable points to my thesis folder in Google Drive. I've organized my 85 PDFs into 5 phases:
> - Phase 1: Theoretical Foundation
> - Phase 2: Sectoral and Business Transitions
> - Phase 3: Context and Case Studies
> - Phase 4: Methodology
> - Phase 5: Business Formation Literature
>
> **Important**: You'll need to update `BASE_PATH` to match YOUR Google Drive folder structure."

**After running:**
> "The cell verifies all paths exist and counts our PDFs. You can see we have [X] PDFs across all phases."

---

## CELL 8-9: Initialize Pipeline Components

**What it does:** Loads the embedding model and initializes ChromaDB

**Say:**
> "Step 4 initializes our core components. This is where the magic happens.
>
> First, we load the **embedding model** - we're using `BAAI/bge-base-en-v1.5`. This model converts text into 768-dimensional vectors that capture semantic meaning. Two sentences about the same topic will have similar vectors, even if they use different words.
>
> We set:
> - **Chunk size to 1000 characters** - this determines how we split documents
> - **Chunk overlap to 200 characters** - so context isn't lost at boundaries
> - **Batch size to 64** - to maximize GPU throughput
>
> Then we initialize **ChromaDB**, our vector database. ChromaDB stores our embeddings and enables fast similarity search."

**After running:**
> "You can see the model loaded on CUDA - that means it's using the GPU. The GPU memory shows how much we're using so far."

---

## CELL 10-11: PDF Processing Functions

**What it does:** Defines functions to extract text from PDFs

**Say:**
> "Step 5 defines our PDF processing functions. We have two main functions:
>
> 1. **`process_pdf()`** - Takes a single PDF and extracts text from each page using PyMuPDF. Each page becomes a separate Document with metadata like the filename, page number, and total pages.
>
> 2. **`process_multiple_pdfs()`** - Processes an entire folder of PDFs. It recursively finds all PDFs and calls the first function on each one.
>
> This gives us granular page-level chunks that we can cite precisely later."

---

## CELL 12-13: Quick Test (2 PDFs)

**What it does:** Tests the pipeline with just 2 PDFs before processing all 85

**Say:**
> "Step 6 is our quick test. Before committing to processing all 85 PDFs, we test with just 2 to make sure everything works.
>
> The key part here is the **HierarchicalNodeParser**. It creates chunks at three levels:
> - 2048 characters (parent chunks for broader context)
> - 1024 characters (child chunks)
> - 512 characters (leaf chunks for precise retrieval)
>
> **Important change from the original**: We're indexing ALL nodes, not just leaf nodes. This means we store both the big-picture context AND the fine details. This matches how our MCP system works and gives us about 4 times more chunks - around 13,000 instead of 3,500."

**After running:**
> "You can see we processed [X] documents and created [X] chunks in about [X] seconds. That's the power of GPU acceleration."

---

## CELL 14-17: Configure LLM (Groq)

**What it does:** Installs and configures Groq as our LLM for generating responses

**Say:**
> "Step 7 sets up our Large Language Model for answering questions. We're using **Groq**, which provides free API access to Llama 3.3 70B.
>
> Why Groq instead of OpenAI?
> 1. It's **free** - no API costs
> 2. It's **fast** - Groq's hardware is optimized for LLM inference
> 3. Llama 3.3 70B is **highly capable** - comparable to GPT-4
>
> You'll need to:
> 1. Get a free API key from console.groq.com
> 2. Add it to Colab secrets as `GROQ_API_KEY`"

**After running cell 17:**
> "Now we have Groq configured with the Llama 3.3 70B model. The free tier allows 30 requests per minute, which is plenty for research use."

---

## CELL 18-19: Test Queries

**What it does:** Creates query engine and tests it with sample questions

**Say:**
> "Now we create our query engine. The `as_query_engine()` method combines:
> - **Retrieval**: Finding the 5 most relevant chunks using similarity search
> - **Response generation**: Using Groq to synthesize an answer
>
> The `response_mode='compact'` setting condenses multiple chunks into a coherent response.
>
> Let's test with a query about spatial econometrics..."

**After running:**
> "Look at the response - it's synthesized from our PDF content. Below you can see the **Sources** - these are the actual PDFs and page numbers the answer came from. This is the power of RAG - we get answers grounded in our actual documents, not hallucinated information."

---

## CELL 20-21: Interactive Query Cell

**What it does:** Reusable cell for custom queries

**Say:**
> "Step 8 gives us an interactive query cell. You can modify the `user_query` variable and run this cell multiple times with different questions.
>
> Notice we also show the **similarity scores** for each source. Higher scores mean the chunk was more relevant to our query."

---

## CELL 22-23: Full Pipeline (All 85 PDFs)

**What it does:** Processes ALL PDFs - the main production run

**Say:**
> "Step 9 is the full pipeline. This processes all 85 PDFs across all 5 phases. It's the same code as our quick test, but without the `max_pdfs` limit.
>
> **Important notes:**
> - This takes 15-20 minutes on A100
> - We use `gc.collect()` after each phase to free memory
> - We're creating hierarchical chunks at 3 levels
> - We index ALL nodes, not just leaf nodes
>
> After this runs, you should see around 13,000+ total chunks - that's our complete searchable knowledge base."

---

## CELL 24-25: Save Index to Google Drive

**What it does:** Persists the ChromaDB index so you don't have to rebuild it

**Say:**
> "Step 10 saves our index to Google Drive. This is crucial - you don't want to rebuild the index every session.
>
> We copy the entire ChromaDB folder to your Drive. Next time, you can reload it instead of reprocessing all PDFs."

---

## CELL 26: Citation System Overview (Markdown)

**What it shows:** Documentation for the citation system

**Say:**
> "This markdown cell documents our citation system. After running the full pipeline, you'll have:
> 1. A **CSV file** with all 85 citations - sortable in Excel
> 2. A **Markdown file** - human-readable reference list
> 3. A **JSON file** - machine-readable with full page content
>
> Plus the `verify_citation()` function to check if citations actually exist in your PDFs."

---

## CELL 27: Reload Existing Index

**What it does:** Loads a previously saved index from Google Drive

**Say:**
> "This cell is for when you come back later. Instead of reprocessing 85 PDFs, you can reload the saved index from Google Drive. It takes just a few seconds.
>
> Just update `SAVED_INDEX_PATH` to point to where you saved the ChromaDB folder."

---

## CELL 28: PDF Metadata Extraction

**What it does:** Extracts metadata (title, author, etc.) from all PDFs

**Say:**
> "Now we enter the Citation System. Step 1 extracts metadata from each PDF using PyMuPDF.
>
> We pull out:
> - Title and author from PDF metadata
> - Page count
> - Keywords if available
>
> Many academic PDFs have this metadata embedded, but some don't - that's why we also parse filenames."

---

## CELL 29: Generate APA Citations with Groq

**What it does:** Uses AI to generate proper APA 7th edition citations

**Say:**
> "Step 2 uses Groq to generate APA citations. For each PDF, we send the metadata to Llama 3.3 70B and ask it to:
> 1. Parse the filename to extract author names and year
> 2. Determine the source type (journal, book, report)
> 3. Generate a proper APA 7th edition citation
>
> This handles messy filenames like `2012_Thelen_Varieties_Liberalization.pdf` and turns them into proper citations.
>
> **Note**: This takes 15-20 minutes for 85 PDFs because of rate limiting. We add a 2-second delay between batches to stay within Groq's free tier limits."

---

## CELL 30: Build Page-Level Content Index

**What it does:** Creates searchable index of every page in every PDF

**Say:**
> "Step 3 builds a page-level content index. For each PDF, we extract the full text of every page.
>
> This enables our citation verification tool - we can check if a specific quote actually appears on a specific page. With about 2,900 pages across 85 PDFs, this is a comprehensive index."

---

## CELL 31: Citation Verification Tool

**What it does:** Defines the `verify_citation()` function

**Say:**
> "Step 4 creates our citation verification tool. The `verify_citation()` function takes:
> - Author name
> - Publication year
> - Page number
> - Optionally, a quote to verify
>
> It returns whether the citation exists, the full APA citation, and a preview of the page content. If the quote doesn't match exactly, it uses fuzzy matching to show similar content.
>
> This is essential for academic integrity - no more accidental page number errors or misquoted passages."

---

## CELL 32: Export Citation Database

**What it does:** Saves citations to CSV, Markdown, and JSON files

**Say:**
> "Step 5 exports everything to three formats:
>
> 1. **CSV** - Perfect for Excel, sortable by author, year, or phase
> 2. **Markdown** - Human-readable, organized by research phase
> 3. **JSON** - Machine-readable, includes page content index
>
> These files are saved to your Google Drive so you can access them anytime."

---

## CELL 33: Test Citation Verification

**What it does:** Runs test cases to verify the citation system works

**Say:**
> "Step 6 tests our verification system with known citations. I've included test cases from my actual thesis:
>
> - Hall & Soskice 2001, page 355 - should verify successfully
> - Hall & Gingerich 2009, page 4 - should verify
> - A known bad page number - should fail appropriately
>
> This shows how the system catches citation errors before they make it into your final paper."

---

## CELL 34-35: Interactive Citation Tools

**What it does:** Search citations and verify specific references

**Say:**
> "Finally, we have interactive tools:
>
> Cell 34 lets you **search** all citations by keyword. Try searching for 'varieties of capitalism' or 'spatial' to find relevant papers.
>
> Cell 35 is for **verification**. Just fill in the author, year, page number, and optionally a quote. The system tells you if it's valid and shows the actual page content."

---

## CELLS 36-72: Example Queries (Optional)

**Say:**
> "The remaining cells are example queries I used while writing my thesis. They cover topics like:
> - Panel methods and spatial econometrics
> - Research design for mixed methods
> - Case selection strategies
> - Data measurement approaches
>
> You can use these as templates for your own queries, or skip them if you just want the core RAG functionality."

---

## CLOSING

**Say:**
> "That's the complete walkthrough! To recap what we built:
>
> 1. A **hierarchical RAG system** with 13,000+ searchable chunks
> 2. **GPU-accelerated processing** using Colab's A100
> 3. **Free LLM integration** via Groq's Llama 3.3 70B
> 4. A **citation verification system** to ensure academic integrity
> 5. **Exportable citation database** in multiple formats
>
> The best part? Once you've built the index, you can reload it instantly in future sessions. No more waiting hours to reprocess your PDFs.
>
> If you have questions, check the documentation or leave a comment. Thanks for watching!"

---

## Quick Reference: Key Variables to Customize

| Variable | Location | What to Change |
|----------|----------|----------------|
| `BASE_PATH` | Cell 7 | Your Google Drive thesis folder path |
| `PDF_FOLDERS` | Cell 7 | Your phase folder names |
| `GROQ_API_KEY` | Colab Secrets | Your Groq API key |
| `chunk_sizes` | Cell 13, 23 | Adjust if memory issues |
| `similarity_top_k` | Cell 18 | Number of sources to retrieve (default: 5) |

---

## Troubleshooting Tips to Mention

1. **"No GPU found"** - Go to Runtime > Change runtime type > A100 GPU
2. **Rate limit errors** - Increase the `time.sleep()` delay in cell 29
3. **Out of memory** - Reduce `embed_batch_size` from 64 to 32
4. **Path not found** - Double-check your Google Drive folder names match exactly
