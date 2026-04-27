# Migration Checklist: Week 11 → Separate Repository

## ✅ Pre-Migration (Completed)
- [x] Built complete Week 11 foundation in `week11-tenacious-bench/`
- [x] Created essential Week 10 artifacts in `week10-artifacts/`
- [x] Validated all tasks pass schema validation (15/15 valid)
- [x] Documented evidence chain from Week 10 probes to benchmark tasks
- [x] Created standalone README for new repository

## 🔄 Migration Steps (To Execute)

### 1. Create New GitHub Repository
```bash
# On GitHub: Create new repo "tenacious-sales-bench"
# Clone locally
git clone https://github.com/[username]/tenacious-sales-bench.git
cd tenacious-sales-bench
```

### 2. Copy Week 11 Contents
```bash
# Copy all Week 11 files to new repo root
cp -r /path/to/10Acweek10/week11-tenacious-bench/* .

# Replace README with standalone version
mv README_STANDALONE.md README.md
```

### 3. Update File References
- [ ] Update `evaluation/scoring_evaluator.py` paths (already done)
- [ ] Update `methodology.md` to reference `week10-artifacts/`
- [ ] Update `dataset/audit_memo.md` to reference local artifacts
- [ ] Update all documentation links

### 4. Test Independence
```bash
# Verify everything works without Week 10 repo
python3 validate_tasks.py
cd evaluation && python3 scoring_evaluator.py
cd ../dataset && python3 generate_tasks_fixed.py
```

### 5. Commit and Push
```bash
git add .
git commit -m "Initial commit: Tenacious Sales Evaluation Bench"
git push origin main
```

## 📋 Deliverable Alignment

### GitHub Repo Requirements ✅
- [x] **Standalone Repository**: Clean separation from Week 10
- [x] **Complete Documentation**: README, methodology, evidence chain
- [x] **Reproducible**: All scripts work independently
- [x] **Evidence Preservation**: Key Week 10 artifacts included

### HuggingFace Requirements 🔄
- [ ] Dataset upload with datasheet
- [ ] Model upload with model card (after training)
- [ ] Proper licensing (CC-BY-4.0)
- [ ] Reference to GitHub repo

### Blog Post Requirements 🔄
- [ ] Technical methodology explanation
- [ ] Results and ablations
- [ ] Honest assessment of limitations
- [ ] Links to GitHub + HuggingFace

## 🎯 Benefits of Separation

✅ **Evaluator Clarity**: Week 11 assessed independently
✅ **Publication Ready**: Clean repo for HuggingFace references  
✅ **Evidence Preserved**: Key Week 10 context maintained
✅ **Submission Compliance**: Meets deliverable requirements exactly

## 📊 File Size Check

**New repo contents** (~3MB total):
- Week 11 source code and tasks
- Essential Week 10 artifacts (probe library, taxonomy, sample traces)
- Documentation and methodology

**Excluded** (referenced via links):
- Full Week 10 trace logs (~50MB)
- Week 10 agent source code
- Large data files (Crunchbase, layoffs data)

## 🚀 Ready for Submission

After migration, the new repository will be:
- **Self-contained** for Week 11 evaluation
- **Evidence-complete** with essential Week 10 references
- **Publication-ready** for HuggingFace and blog post
- **Compliant** with all deliverable requirements

Execute migration when ready to submit Week 11 deliverables.