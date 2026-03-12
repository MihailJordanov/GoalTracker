document.addEventListener("DOMContentLoaded", () => {
    const dataElement = document.getElementById("play-time-data");

    const monthLabels = JSON.parse(dataElement.dataset.monthLabels || "[]");
    const years = JSON.parse(dataElement.dataset.years || "[]");
    const allTimeCounts = JSON.parse(dataElement.dataset.allTimeCounts || "[]");
    const yearlyData = JSON.parse(dataElement.dataset.yearlyData || "{}");
    const teamName = JSON.parse(dataElement.dataset.teamName || '"Отбор"');

    const yearFilter = document.getElementById("yearFilter");
    const totalMatchesValue = document.getElementById("totalMatchesValue");
    const activeMonthsValue = document.getElementById("activeMonthsValue");
    const bestMonthValue = document.getElementById("bestMonthValue");
    const monthsGrid = document.getElementById("monthsGrid");
    const chartTitle = document.getElementById("chartTitle");
    const chartSubtitle = document.getElementById("chartSubtitle");

    const ctx = document.getElementById("playTimeChart");

    function getCountsBySelection(selectedValue) {
        if (selectedValue === "all") {
            return allTimeCounts;
        }

        return yearlyData[selectedValue] || yearlyData[parseInt(selectedValue, 10)] || new Array(12).fill(0);
    }

    function calculateSummary(counts) {
        const total = counts.reduce((sum, value) => sum + value, 0);
        const activeMonths = counts.filter(value => value > 0).length;

        let maxValue = Math.max(...counts);
        let bestMonth = "-";

        if (maxValue > 0) {
            const bestMonthIndex = counts.findIndex(value => value === maxValue);
            bestMonth = `${monthLabels[bestMonthIndex]} (${maxValue})`;
        }

        return {
            total,
            activeMonths,
            bestMonth
        };
    }

    function renderMonthsGrid(counts) {
        monthsGrid.innerHTML = "";

        monthLabels.forEach((month, index) => {
            const value = counts[index] || 0;

            const item = document.createElement("div");
            item.className = "month-box";

            item.innerHTML = `
                <div class="month-box-name">${month}</div>
                <div class="month-box-value">${value}</div>
                <div class="month-box-bar">
                    <span style="width: ${Math.max(value * 12, value > 0 ? 14 : 0)}px;"></span>
                </div>
            `;

            monthsGrid.appendChild(item);
        });
    }

    function updateStats(counts) {
        const summary = calculateSummary(counts);

        totalMatchesValue.textContent = summary.total;
        activeMonthsValue.textContent = summary.activeMonths;
        bestMonthValue.textContent = summary.bestMonth;
    }

    function getSubtitleText(selectedValue) {
        if (selectedValue === "all") {
            return "Показани данни: цяло време";
        }
        return `Показани данни: ${selectedValue} година`;
    }

    const chart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: monthLabels,
            datasets: [
                {
                    label: "Изиграни мачове",
                    data: allTimeCounts,
                    borderWidth: 2,
                    borderRadius: 10,
                    borderSkipped: false,
                    backgroundColor: "rgba(57, 255, 20, 0.22)",
                    borderColor: "rgba(57, 255, 20, 1)",
                    hoverBackgroundColor: "rgba(57, 255, 20, 0.35)",
                    hoverBorderColor: "rgba(120, 255, 98, 1)"
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
            plugins: {
                legend: {
                    labels: {
                        color: "#e7ffe7",
                        font: {
                            size: 13
                        }
                    }
                },
                title: {
                    display: false
                },
                tooltip: {
                    backgroundColor: "rgba(10, 10, 10, 0.96)",
                    titleColor: "#39ff14",
                    bodyColor: "#eaffea",
                    borderColor: "rgba(57, 255, 20, 0.45)",
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: "#c9f7cb",
                        maxRotation: 0,
                        minRotation: 0
                    },
                    grid: {
                        color: "rgba(57, 255, 20, 0.08)"
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        stepSize: 1,
                        color: "#c9f7cb"
                    },
                    grid: {
                        color: "rgba(57, 255, 20, 0.08)"
                    }
                }
            }
        }
    });

    function updateView(selectedValue) {
        const counts = getCountsBySelection(selectedValue);

        chart.data.datasets[0].data = counts;
        chart.update();

        updateStats(counts);
        renderMonthsGrid(counts);

        chartTitle.textContent = `Изиграни мачове по месеци · ${teamName}`;
        chartSubtitle.textContent = getSubtitleText(selectedValue);
    }

    yearFilter.addEventListener("change", (e) => {
        updateView(e.target.value);
    });

    updateView("all");
});