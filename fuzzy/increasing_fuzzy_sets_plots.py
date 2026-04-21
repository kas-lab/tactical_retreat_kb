# Copyright 2025 KAS Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Generate example membership functions and plots hitting ~1 at x=10
import matplotlib.pyplot as plt

import numpy as np

# Target x and target membership levels to demonstrate
x_star = 10.0
targets = [0.95, 0.99]

xs = np.linspace(0, 15, 400)

# --- Exponential saturation: mu = 1 - exp(-k x) ---


def k_from_target_exp(mu_star, x_star):
    # mu_star = 1 - exp(-k x_star) -> k = -ln(1 - mu_star)/x_star
    return -np.log(1.0 - mu_star) / x_star


plt.figure()
for mu_star in targets:
    k = k_from_target_exp(mu_star, x_star)
    mu = 1 - np.exp(-k * xs)
    plt.plot(xs, mu, label=f'μ*= {mu_star}, k={k:.4f}')
# Mark the reference x=10 vertical
plt.axvline(x_star, linestyle='--', linewidth=1)
plt.title('Exponential saturation: μ(x) = 1 - e^{-k x}')
plt.xlabel('x')
plt.ylabel('μ(x)')
plt.ylim(-0.05, 1.05)
plt.legend()
plt.grid(True, linestyle=':', linewidth=0.5)
exp_path = '/mnt/data/fuzzy_exp_saturation.png'
plt.savefig(exp_path, dpi=160, bbox_inches='tight')
plt.show()

# --- Logistic: mu = 1 / (1 + exp(-k (x - x0))) ---
# We'll choose x0=5 as the inflection point and solve k to hit targets at x=10.


def k_from_target_logistic(mu_star, x_star, x0):
    # mu_star = 1 / (1 + exp(-k(x_star - x0)))
    # -> 1/mu_star - 1 = exp(-k(x_star - x0))
    # -> k = - ln(1/mu_star - 1) / (x_star - x0)
    return -np.log(1.0 / mu_star - 1.0) / (x_star - x0)


x0 = 5.0
plt.figure()
for mu_star in targets:
    k = k_from_target_logistic(mu_star, x_star, x0)
    mu = 1.0 / (1.0 + np.exp(-k * (xs - x0)))
    plt.plot(xs, mu, label=f'μ*= {mu_star}, k={k:.4f}, x0={x0}')
plt.axvline(x_star, linestyle='--', linewidth=1)
plt.title('Logistic (sigmoid): μ(x) = 1 / (1 + e^{-k(x - x0)})')
plt.xlabel('x')
plt.ylabel('μ(x)')
plt.ylim(-0.05, 1.05)
plt.legend()
plt.grid(True, linestyle=':', linewidth=0.5)
log_path = '/mnt/data/fuzzy_logistic.png'
plt.savefig(log_path, dpi=160, bbox_inches='tight')
plt.show()

# --- Rational: mu = x / (x + a) ---


def a_from_target_rational(mu_star, x_star):
    # mu_star = x_star / (x_star + a) -> a = x_star*(1/mu_star - 1)
    return x_star * (1.0 / mu_star - 1.0)


plt.figure()
for mu_star in targets:
    a = a_from_target_rational(mu_star, x_star)
    mu = xs / (xs + a)
    plt.plot(xs, mu, label=f'μ*= {mu_star}, a={a:.4f}')
plt.axvline(x_star, linestyle='--', linewidth=1)
plt.title('Rational: μ(x) = x / (x + a)')
plt.xlabel('x')
plt.ylabel('μ(x)')
plt.ylim(-0.05, 1.05)
plt.legend()
plt.grid(True, linestyle=':', linewidth=0.5)
rat_path = '/mnt/data/fuzzy_rational.png'
plt.savefig(rat_path, dpi=160, bbox_inches='tight')
plt.show()

exp_path, log_path, rat_path
