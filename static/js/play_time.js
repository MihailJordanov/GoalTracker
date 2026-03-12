document.addEventListener("DOMContentLoaded", () => {
    const dataElement = document.getElementById("play-time-data");

    const monthLabels = JSON.parse(dataElement.dataset.monthLabels || "[]");
    const years = JSON.parse(dataElement.dataset.years || "[]");
    const yearlyData = JSON.parse(dataElement.dataset.yearlyData || "{}");
    const allTimeLabels = JSON.parse(dataElement.dataset.allTimeLabels || "[]");
    const allTimeCounts = JSON.parse(dataElement.dataset.allTimeCounts || "[]");
    const teamName = JSON.parse(dataElement.dataset.teamName || '"Team"');

    const yearFilter = document.getElementById("yearFilter");
    const totalMatchesValue = document.getElementById("totalMatchesValue");
    const activeMonthsValue = document.getElementById("activeMonthsValue");
    const bestMonthValue = document.getElementById("bestMonthValue");
    const monthsGrid = document.getElementById("monthsGrid");
    const chartTitle = document.getElementById("chartTitle");
    const chartSubtitle = document.getElementById("chartSubtitle");
    const gridTitle = document.getElementById("gridTitle");
    const chartTypeButtons = document.querySelectorAll(".chart-toggle-btn");

    let currentChartType = "bar";

    function formatTimelineLabel(label) {
        const [year, month] = label.split("-");
        const monthIndex = parseInt(month, 10) - 1;
        return `${monthLabels[monthIndex]} ${year}`;
    }

    function getDatasetBySelection(selectedValue) {
        if (selectedValue === "all") {
            return {
                labels: allTimeLabels.map(formatTimelineLabel),
                rawLabels: allTimeLabels,
                counts: allTimeCounts,
                mode: "timeline"
            };
        }

        const counts = yearlyData[selectedValue] || yearlyData[parseInt(selectedValue, 10)] || new Array(12).fill(0);

        return {
            labels: monthLabels,
            rawLabels: monthLabels,
            counts: counts,
            mode: "year"
        };
    }

    function calculateSummary(labels, counts, mode) {
        const total = counts.reduce((sum, value) => sum + value, 0);
        const activeMonths = counts.filter(value => value > 0).length;

        let maxValue = Math.max(...counts, 0);
        let bestLabel = "-";

        if (maxValue > 0) {
            const bestIndex = counts.findIndex(value => value === maxValue);

            if (mode === "timeline") {
                bestLabel = `${formatTimelineLabel(labels[bestIndex])} (${maxValue})`;
            } else {
                bestLabel = `${labels[bestIndex]} (${maxValue})`;
            }
        }

        return {
            total,
            activeMonths,
            bestLabel
        };
    }

    function renderBreakdown(dataset, selectedValue) {
        monthsGrid.innerHTML = "";

        if (selectedValue === "all") {
            gridTitle.textContent = "Timeline Breakdown";

            dataset.rawLabels.forEach((rawLabel, index) => {
                const value = dataset.counts[index] || 0;

                const item = document.createElement("div");
                item.className = "month-box";

                item.innerHTML = `
                    <div class="month-box-name">${formatTimelineLabel(rawLabel)}</div>
                    <div class="month-box-value">${value}</div>
                    <div class="month-box-bar">
                        <span style="width: ${Math.max(value * 12, value > 0 ? 14 : 0)}px;"></span>
                    </div>
                `;

                monthsGrid.appendChild(item);
            });

            return;
        }

        gridTitle.textContent = "Monthly Breakdown";

        dataset.labels.forEach((label, index) => {
            const value = dataset.counts[index] || 0;

            const item = document.createElement("div");
            item.className = "month-box";

            item.innerHTML = `
                <div class="month-box-name">${label}</div>
                <div class="month-box-value">${value}</div>
                <div class="month-box-bar">
                    <span style="width: ${Math.max(value * 12, value > 0 ? 14 : 0)}px;"></span>
                </div>
            `;

            monthsGrid.appendChild(item);
        });
    }

    function updateStats(dataset) {
        const summary = calculateSummary(dataset.rawLabels, dataset.counts, dataset.mode);

        totalMatchesValue.textContent = summary.total;
        activeMonthsValue.textContent = summary.activeMonths;
        bestMonthValue.textContent = summary.bestLabel;
    }

    function getSubtitleText(selectedValue) {
        if (selectedValue === "all") {
            return "Showing data for: All Time timeline";
        }
        return `Showing data for: ${selectedValue}`;
    }

    function getDatasetStyle(chartType) {
        if (chartType === "line") {
            return {
                type: "line",
                backgroundColor: "rgba(0, 255, 183, 0.12)",
                borderColor: "rgba(0, 255, 183, 1)",
                pointBackgroundColor: "rgba(0, 255, 183, 1)",
                pointBorderColor: "rgba(255,255,255,0.9)",
                pointBorderWidth: 1.5,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointHitRadius: 14,
                fill: true,
                tension: 0.35,
                cubicInterpolationMode: "monotone",
                borderWidth: 3
            };
        }

        return {
            type: "bar",
            backgroundColor: "rgba(0, 255, 183, 0.22)",
            borderColor: "rgba(0, 255, 183, 1)",
            hoverBackgroundColor: "rgba(0, 255, 183, 0.32)",
            hoverBorderColor: "rgba(102, 255, 214, 1)",
            borderWidth: 2,
            borderRadius: 10,
            borderSkipped: false
        };
    }

    const ctx = document.getElementById("playTimeChart");

    const initialDataset = getDatasetBySelection("all");

    const chart = new Chart(ctx, {
        type: currentChartType,
        data: {
            labels: initialDataset.labels,
            datasets: [
                {
                    label: "Matches Played",
                    data: initialDataset.counts,
                    ...getDatasetStyle(currentChartType)
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 650,
                easing: "easeOutQuart"
            },
            interaction: {
                intersect: false,
                mode: "index"
            },
            plugins: {
                legend: {
                    labels: {
                        color: "#e8f7f0",
                        font: {
                            size: 13
                        }
                    }
                },
                tooltip: {
                    backgroundColor: "rgba(11, 15, 20, 0.96)",
                    titleColor: "#00ffb7",
                    bodyColor: "#e8f7f0",
                    borderColor: "rgba(0,255,183,0.28)",
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: "#9fb2c3",
                        maxRotation: 45,
                        minRotation: 0
                    },
                    grid: {
                        color: "rgba(255,255,255,0.05)"
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        stepSize: 1,
                        color: "#9fb2c3"
                    },
                    grid: {
                        color: "rgba(255,255,255,0.05)"
                    }
                }
            }
        }
    });

    function setActiveToggle(type) {
        chartTypeButtons.forEach(btn => {
            btn.classList.toggle("active", btn.dataset.chartType === type);
        });
    }

    function updateView() {
        const selectedValue = yearFilter.value;
        const dataset = getDatasetBySelection(selectedValue);
        const style = getDatasetStyle(currentChartType);

        chart.config.type = currentChartType;
        chart.data.labels = dataset.labels;
        chart.data.datasets[0].label = "Matches Played";
        chart.data.datasets[0].data = dataset.counts;

        Object.keys(chart.data.datasets[0]).forEach(key => {
            if (!["label", "data"].includes(key)) {
                delete chart.data.datasets[0][key];
            }
        });

        Object.assign(chart.data.datasets[0], style);

        chart.update();

        updateStats(dataset);
        renderBreakdown(dataset, selectedValue);

        chartTitle.textContent = `Matches Played Over Time · ${teamName}`;
        chartSubtitle.textContent = getSubtitleText(selectedValue);
    }

    yearFilter.addEventListener("change", updateView);

    chartTypeButtons.forEach(button => {
        button.addEventListener("click", () => {
            currentChartType = button.dataset.chartType;
            setActiveToggle(currentChartType);
            updateView();
        });
    });

    setActiveToggle(currentChartType);
    updateView();
});