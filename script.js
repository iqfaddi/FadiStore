const SUPABASE_URL = "https://hcuorfjumfurcxrvvsmw.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhjdW9yZmp1bWZ1cmN4cnZ2c213Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg1MTM4OTYsImV4cCI6MjA5NDA4OTg5Nn0.9gGg0d7YTWyMhGlIE8KebDisRQi8V1jprLfXc3lT2jE";

const grid = document.getElementById("servicesGrid");
const modal = document.getElementById("modal");
const modalTitle = document.getElementById("modalTitle");
const plansContainer = document.getElementById("plansContainer");
const priceValue = document.getElementById("priceValue");
const buyBtn = document.getElementById("buyBtn");

let servicesMap = {};
let currentService = "";
let currentPlan = "";
let currentPrice = "";

async function loadProducts() {
  try {
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/products?select=*&order=id.asc`,
      {
        headers: {
          apikey: SUPABASE_KEY,
          Authorization: `Bearer ${SUPABASE_KEY}`
        }
      }
    );

    const products = await res.json();
    servicesMap = {};

    products.forEach((p) => {
      const service = p.name?.trim();
      if (!service) return;

      if (!servicesMap[service]) {
        servicesMap[service] = [];
      }

      servicesMap[service].push({
        ...p,
        label: p.duration?.trim() || ""
      });
    });

    renderServices();

  } catch (err) {
    console.error("Failed loading products:", err);
  }
}

function renderServices() {
  grid.innerHTML = "";

  Object.keys(servicesMap).forEach((service) => {
    const first = servicesMap[service][0];

    const card = document.createElement("div");
    card.className = "service-card";

    card.innerHTML = `
      <div class="img-box">
        <img src="${first.image}" alt="${service}">
      </div>
      <span>${service}</span>
    `;

    card.onclick = () => openModal(service);

    grid.appendChild(card);
  });
}

function openModal(service) {
  currentService = service;
  modalTitle.textContent = service;
  plansContainer.innerHTML = "";

  const plans = servicesMap[service];

  plans.forEach((plan, index) => {
    const planCard = document.createElement("div");
    planCard.className = "plan-option";

    planCard.innerHTML = `
      <div class="plan-title">${plan.label}</div>
      <div class="plan-price">$${plan.price}</div>
    `;

    planCard.onclick = () => {
      document.querySelectorAll(".plan-option").forEach(el => {
        el.classList.remove("active");
      });

      planCard.classList.add("active");
      selectPlan(plan);
    };

    if (index === 0) {
      planCard.classList.add("active");
      selectPlan(plan);
    }

    plansContainer.appendChild(planCard);
  });

  modal.classList.remove("hidden");
}

function selectPlan(plan) {
  currentPlan = plan.label;
  currentPrice = plan.price;

  priceValue.textContent = `$${plan.price}`;

  const msg = `Hello 👋
I would like to order:

📦 Product: ${currentService}
⏳ Duration: ${currentPlan}
💵 Price: ${currentPrice}

Thank you.`;

  buyBtn.href = `https://wa.me/9613177862?text=${encodeURIComponent(msg)}`;
}

document.getElementById("closeModal").onclick = () => {
  modal.classList.add("hidden");
};

document.getElementById("cancelBtn").onclick = () => {
  modal.classList.add("hidden");
};

modal.onclick = (e) => {
  if (e.target === modal) {
    modal.classList.add("hidden");
  }
};

loadProducts();
