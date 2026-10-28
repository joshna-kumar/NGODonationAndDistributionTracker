/* ==========================================================================
   Chart.js Analytics Dashboard Manager
   ========================================================================== */

const ChartManager = {
  charts: {},

  async loadAnalytics() {
    try {
      const res = await fetch('/api/reports/analytics');
      const data = await res.json();
      this.renderCharts(data);
    } catch (err) {
      console.error('Failed to load chart analytics:', err);
    }
  },

  renderCharts(data) {
    if (typeof Chart === 'undefined') {
      console.warn('Chart.js library not loaded yet');
      return;
    }

    // Chart Palette (Lavenders & Complementary Pastels)
    const lavenderPalette = [
      '#C9B8E8', '#6B5B95', '#E6DFF5', '#A8E6CF',
      '#FFD3B6', '#FFAAA5', '#81C784', '#64B5F6'
    ];

    // 1. Donations by Category (Doughnut Chart)
    const ctxCat = document.getElementById('chart-category-split');
    if (ctxCat) {
      if (this.charts.cat) this.charts.cat.destroy();
      this.charts.cat = new Chart(ctxCat, {
        type: 'doughnut',
        data: {
          labels: data.donations_by_category.labels,
          datasets: [{
            data: data.donations_by_category.amounts,
            backgroundColor: lavenderPalette,
            borderWidth: 2,
            borderColor: '#FFFFFF'
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 12 } } },
            tooltip: {
              callbacks: {
                label: (ctx) => ` ${ctx.label}: ₹${ctx.raw.toLocaleString('en-IN')}`
              }
            }
          }
        }
      });
    }

    // 2. Inventory Stock Levels (Bar Chart with Demand status)
    const ctxInv = document.getElementById('chart-inventory-levels');
    if (ctxInv) {
      if (this.charts.inv) this.charts.inv.destroy();
      this.charts.inv = new Chart(ctxInv, {
        type: 'bar',
        data: {
          labels: data.inventory_levels.labels,
          datasets: [
            {
              label: 'Available Quantity',
              data: data.inventory_levels.quantities,
              backgroundColor: '#C9B8E8',
              borderRadius: 6,
              barPercentage: 0.35,
              categoryPercentage: 0.5
            },
            {
              label: 'Demand (Low Stock Threshold)',
              data: data.inventory_levels.thresholds,
              backgroundColor: '#6B5B95',
              borderRadius: 6,
              barPercentage: 0.35,
              categoryPercentage: 0.5
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          aspectRatio: 1.5,
          plugins: {
            legend: { display: true, position: 'top' }
          },
          scales: {
            y: { beginAtZero: true, title: { display: true, text: 'Units in Stock' } }
          }
        }
      });
    }

    // 3. Beneficiaries Served by Category (Pie Chart)
    const ctxBen = document.getElementById('chart-beneficiary-category');
    if (ctxBen) {
      if (this.charts.ben) this.charts.ben.destroy();
      this.charts.ben = new Chart(ctxBen, {
        type: 'pie',
        data: {
          labels: data.beneficiaries_by_category.labels,
          datasets: [{
            data: data.beneficiaries_by_category.counts,
            backgroundColor: ['#E6DFF5', '#C9B8E8', '#6B5B95', '#A8E6CF', '#FFD3B6']
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { position: 'bottom' }
          }
        }
      });
    }
  }
};
