#!/bin/bash
# Quick Correction Engine - Complete Training Pipeline
# This script runs all steps to train and export the Quick Correction Model

set -e  # Exit on error

echo "=========================================="
echo "Quick Correction Engine - Training Pipeline"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Generate Training Data
echo -e "${YELLOW}Step 1/3: Generating synthetic training data...${NC}"
cd ml/synthetic_data
python generator.py

if [ ! -f ../quick_correction/data/train.jsonl ]; then
    echo -e "${RED}Error: Training data not generated${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Training data generated${NC}"
echo ""

# Step 2: Train Model
echo -e "${YELLOW}Step 2/3: Training base model (this may take 2-12 hours)...${NC}"
cd ../quick_correction
python train.py

if [ ! -d models/quick_correction_base_v1 ]; then
    echo -e "${RED}Error: Model training failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Model trained successfully${NC}"
echo ""

# Step 3: Export to ONNX
echo -e "${YELLOW}Step 3/3: Exporting to ONNX format...${NC}"
python export_onnx.py \
    --model models/quick_correction_base_v1 \
    --output ../../ml/models \
    --test

if [ ! -f ../../ml/models/quick_correction_base_v1/model.onnx ]; then
    echo -e "${RED}Error: ONNX export failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ ONNX export complete${NC}"
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}Training pipeline complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Test backend: cd backend && pytest tests/test_quick_correction.py -v"
echo "  2. Test frontend: cd frontend && npm install && npm run dev"
echo ""
echo "Model location: ml/models/quick_correction_base_v1/model.onnx"
echo ""
