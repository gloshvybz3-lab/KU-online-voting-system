// Kampala University Online Voting System - Main Interactive Scripts

document.addEventListener('DOMContentLoaded', () => {
    // 1. Ballot Selection Interaction
    setupBallotInteractions();

    // 2. Election Countdown Timers
    setupCountdowns();

    // 3. Auto-dismiss alerts after 6 seconds
    setupAlerts();
});

function setupBallotInteractions() {
    const ballotCards = document.querySelectorAll('.candidate-ballot-card');
    ballotCards.forEach(card => {
        card.addEventListener('click', (e) => {
            // Find radio button inside card
            const radio = card.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;

                // Remove selected class from sibling cards in the same position group
                const groupName = radio.getAttribute('name');
                document.querySelectorAll(`input[name="${groupName}"]`).forEach(r => {
                    const parentCard = r.closest('.candidate-ballot-card');
                    if (parentCard) parentCard.classList.remove('selected');
                });

                // Add selected class to this card
                card.classList.add('selected');
            }
        });
    });

    // Confirmation Modal Trigger for Ballot
    const ballotForm = document.getElementById('ballotForm');
    const reviewModal = document.getElementById('reviewChoicesModal');
    const confirmSubmitBtn = document.getElementById('confirmSubmitVoteBtn');

    if (ballotForm && reviewModal && confirmSubmitBtn) {
        ballotForm.addEventListener('submit', (e) => {
            // If already verified through modal, let it submit
            if (ballotForm.dataset.confirmed === 'true') {
                return true;
            }

            e.preventDefault();

            // Populate choices in the modal
            const reviewList = document.getElementById('reviewChoicesList');
            if (reviewList) {
                reviewList.innerHTML = '';
                const positionSections = document.querySelectorAll('.position-section');
                let allAnswered = true;

                positionSections.forEach(sec => {
                    const posTitle = sec.dataset.positionTitle;
                    const posId = sec.dataset.positionId;
                    const selectedRadio = sec.querySelector(`input[name="position_${posId}"]:checked`);

                    const item = document.createElement('div');
                    item.className = 'list-group-item d-flex justify-content-between align-items-center py-2';

                    if (selectedRadio) {
                        const candName = selectedRadio.dataset.candidateName || 'Abstain';
                        const isAbstain = selectedRadio.value === 'abstain';

                        item.innerHTML = `
                            <div>
                                <span class="fw-bold text-dark">${posTitle}</span>
                            </div>
                            <div>
                                <span class="badge ${isAbstain ? 'bg-secondary' : 'bg-primary'} fs-6 px-3 py-1">
                                    ${candName}
                                </span>
                            </div>
                        `;
                    } else {
                        allAnswered = false;
                        item.innerHTML = `
                            <div>
                                <span class="fw-bold text-dark">${posTitle}</span>
                            </div>
                            <div>
                                <span class="badge bg-danger fs-6 px-3 py-1">No selection made</span>
                            </div>
                        `;
                    }
                    reviewList.appendChild(item);
                });

                if (!allAnswered) {
                    alert('Please make a selection (a candidate or Abstain) for all positions before proceeding.');
                    return false;
                }

                // Show bootstrap modal
                const modal = new bootstrap.Modal(reviewModal);
                modal.show();
            }
        });

        confirmSubmitBtn.addEventListener('click', () => {
            confirmSubmitBtn.disabled = true;
            confirmSubmitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Casting Encrypted Vote...';
            ballotForm.dataset.confirmed = 'true';
            ballotForm.submit();
        });
    }
}

function setupCountdowns() {
    const timers = document.querySelectorAll('[data-countdown]');
    timers.forEach(timer => {
        const targetDateStr = timer.getAttribute('data-countdown');
        if (!targetDateStr) return;

        const targetDate = new Date(targetDateStr).getTime();

        const updateTimer = () => {
            const now = new Date().getTime();
            const distance = targetDate - now;

            if (distance < 0) {
                timer.innerHTML = '<span class="text-danger fw-bold">Polls Closed</span>';
                return;
            }

            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            let display = '';
            if (days > 0) display += `${days}d `;
            display += `${hours}h ${minutes}m ${seconds}s`;

            timer.innerText = display;
        };

        updateTimer();
        setInterval(updateTimer, 1000);
    });
}

function setupAlerts() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 7000);
    });
}
