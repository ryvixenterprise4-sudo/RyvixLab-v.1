const ctx = document.getElementById('myChart').getContext('2d');

const myChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Jui', 'Jul', 'Aou', 'Sep', 'Oct', 'Nov', 'Dec'],
        datasets: [{
            label: 'Chiffre d\'Affaires (HTG)',
            data: [50000, 55000, 50000, 48000, 60000, 80000, 60000, 68000, 56000, 51000, 48000, 28000],
            backgroundColor: '#25C0B8', // Couleur noire comme sur votre image
            borderRadius: 5
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: false } // Masque la légende si non nécessaire
        },
        scales: {
            y: {
                beginAtZero: false, // Commence à 30k comme sur votre image
                min: 10000,
                ticks: {
                    callback: function(value) { return value.toLocaleString() + ' HTG'; }
                }
            }
        }
    }
});