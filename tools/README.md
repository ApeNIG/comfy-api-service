# A/B Testing Tool for ComfyUI

Find the optimal balance between image quality and cost by comparing different generation settings side-by-side.

## Features

- **Preset Test Suites** - Pre-configured tests for common comparisons
- **Custom Configurations** - Define your own test parameters
- **Cost Analysis** - Detailed cost breakdowns and efficiency metrics
- **Side-by-Side Comparison** - Generate images with different settings
- **JSON Reports** - Exportable test results for analysis
- **Smart Recommendations** - Find cost-effective "sweet spots"

## Quick Start

### 1. Quality Comparison
Test different quality levels at the same size:

```bash
python tools/ab_tester.py \
  --preset quality \
  --prompt "A sunset over mountains"
```

This tests:
- Low Quality (15 steps)
- Standard Quality (20 steps)
- High Quality (30 steps)
- Very High Quality (50 steps)

### 2. Size Comparison
Compare different image sizes:

```bash
python tools/ab_tester.py \
  --preset sizes \
  --prompt "Abstract digital art"
```

This tests:
- 512x512 (standard)
- 768x768 (medium)
- 1024x1024 (large)
- 512x768 (portrait)
- 768x512 (landscape)

### 3. Performance Comparison
Find the fastest generation settings:

```bash
python tools/ab_tester.py \
  --preset performance \
  --prompt "Futuristic cityscape"
```

This tests:
- Ultra Fast (10 steps)
- Fast (15 steps)
- Balanced (20 steps)
- Slow (30 steps)

### 4. Comprehensive Test
Run all common configurations:

```bash
python tools/ab_tester.py \
  --preset all \
  --prompt "Professional landscape photo"
```

This runs 6 different configurations covering size and quality combinations.

## Custom Configurations

Define your own test parameters:

```bash
python tools/ab_tester.py \
  --custom "512x512x20,1024x1024x30,768x768x25" \
  --prompt "Your prompt here"
```

Format: `WIDTHxHEIGHTxSTEPS` separated by commas.

## Advanced Usage

### Skip Confirmation
Auto-approve all tests:

```bash
python tools/ab_tester.py \
  --preset quality \
  --prompt "A cat" \
  --yes
```

### Custom Output Directory
Specify where to save results:

```bash
python tools/ab_tester.py \
  --preset sizes \
  --prompt "A sunset" \
  --output my_tests
```

### With Authentication
If your API requires authentication:

```bash
python tools/ab_tester.py \
  --url https://your-api.com \
  --api-key YOUR_API_KEY \
  --preset quality \
  --prompt "A landscape"
```

## Understanding the Results

### Cost Estimation Summary
Before running tests, you'll see:
```
Config Name          Size        Steps  Est. Cost    Est. Time
─────────────────────────────────────────────────────────────────
Low Quality         512x512     15     $0.000094    2s
Standard Quality    512x512     20     $0.000125    3s
High Quality        512x512     30     $0.000188    4s
Very High Quality   512x512     50     $0.000313    7s

Total Estimated Cost: $0.000720
Number of Tests:      4
```

### Test Results
After running, you'll see:
```
Config               Size         Steps  Time     Cost         Status
────────────────────────────────────────────────────────────────────────
Low Quality          512x512      15     2.3s     $0.000094    ✓ Success
Standard Quality     512x512      20     3.1s     $0.000125    ✓ Success
High Quality         512x512      30     4.2s     $0.000188    ✓ Success
Very High Quality    512x512      50     6.8s     $0.000313    ✓ Success
```

### Cost Analysis
Get recommendations for the best value:

```
Most Cost-Effective:
  Low Quality
  Size: 512x512
  Steps: 15
  Cost: $0.000094
  Time: 2.3s

Cost Efficiency (cost per megapixel):
  Low Quality          $0.000359/MP (0.26 MP)
  Standard Quality     $0.000477/MP (0.26 MP)
  High Quality         $0.000717/MP (0.26 MP)
  Very High Quality    $0.001194/MP (0.26 MP)
```

## Output Files

The tool creates:

### Generated Images
```
ab_tests/
├── Low_Quality_20251108_120000.png
├── Standard_Quality_20251108_120001.png
├── High_Quality_20251108_120002.png
└── Very_High_Quality_20251108_120003.png
```

### JSON Report
```json
{
  "prompt": "A sunset over mountains",
  "timestamp": "2025-11-08T12:00:00",
  "results": [
    {
      "config": {
        "name": "Low Quality",
        "width": 512,
        "height": 512,
        "steps": 15
      },
      "estimated_cost": 0.000094,
      "generation_time": 2.3,
      "image_path": "ab_tests/Low_Quality_20251108_120000.png",
      "success": true
    }
  ]
}
```

## Use Cases

### 1. Find Your Sweet Spot
Compare quality levels to find where diminishing returns begin:

```bash
python tools/ab_tester.py \
  --custom "512x512x10,512x512x15,512x512x20,512x512x25,512x512x30,512x512x40,512x512x50" \
  --prompt "Test subject"
```

### 2. Budget Optimization
Test different sizes to maximize quality within budget:

```bash
python tools/ab_tester.py \
  --preset sizes \
  --prompt "Product photo"
```

Then pick the largest size that fits your budget.

### 3. Production Baseline
Establish baseline settings for your production pipeline:

```bash
python tools/ab_tester.py \
  --preset all \
  --prompt "Typical use case prompt"
```

Use results to set standards for your application.

### 4. Quality Assurance
Verify that quality improvements justify cost increases:

```bash
python tools/ab_tester.py \
  --custom "512x512x20,512x512x40" \
  --prompt "Critical quality test"
```

Compare if 2x steps = 2x better quality.

## Tips

1. **Start with presets** - Use built-in presets before creating custom tests
2. **Same prompt** - Use the same prompt across tests for valid comparisons
3. **Review images** - Cost isn't everything; visually compare quality
4. **Check efficiency** - Look at cost-per-megapixel for size comparisons
5. **Save reports** - Keep JSON reports to track improvements over time

## Cost Examples

Real costs for typical tests (RTX 4000 Ada @ $0.15/hour):

| Test Preset | Tests | Total Cost | Time |
|-------------|-------|------------|------|
| Quality     | 4     | ~$0.0007   | ~18s |
| Sizes       | 5     | ~$0.0008   | ~20s |
| Performance | 4     | ~$0.0005   | ~12s |
| All         | 6     | ~$0.0012   | ~30s |

**Total cost to test all presets: < $0.01** (1 penny!)

## Next Steps

After finding optimal settings:

1. Update your application defaults
2. Document recommended settings
3. Set up monitoring for cost tracking
4. Run periodic A/B tests as models improve

## Troubleshooting

**Images look similar:** Try wider step ranges (e.g., 10, 20, 40, 80)

**Tests taking too long:** Use `--preset performance` or custom config with fewer steps

**Want to compare models:** Not yet supported, but coming soon!

**Need more metrics:** Check the JSON report for additional data

## Advanced Scenarios

### Monthly Cost Projection
After finding optimal settings, project monthly costs:

```bash
# Found that 512x512x20 is optimal
python demo/image_generator.py --project 100

# Shows: $0.37/month for 100 images/day
```

### Batch Production
Use optimal settings for batch generation:

```bash
python demo/image_generator.py \
  --width 512 \
  --height 512 \
  --steps 20 \
  --num-images 10 \
  --prompt "Production prompt"
```

## Contributing

Have ideas for new preset tests or analysis metrics? Open an issue!

## License

Part of the ComfyUI API Service project.
