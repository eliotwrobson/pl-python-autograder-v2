import numpy as np
import pytest

from pl_pytest_autograder.fixture import StudentFixture

### Start of simulation code ###


def simulate_stock_price(
    S_0,
    mu_0,
    sigma_0,
    N,
    T=1,
    kappa=1.5,
    theta=0.2,
    eta=0.3,
    seed=42,
) -> np.ndarray:
    """
    Simulates a realistic stock price time series with stochastic drift and
    volatility.

    Parameters:
        S_0: Initial stock price
        mu_0: Initial drift (expected return)
        sigma_0: Initial volatility
        N: Number of time steps
        T: Total time period (in years)
        kappa: Mean reversion speed of volatility
        theta: Long-term average volatility
        eta: Volatility of volatility (vol of vol)

    Returns:
        t: Time points
        S: Simulated stock prices
    """
    dt = T / N  # Time step
    # t = np.linspace(start=0, stop=T, num=N)  # Time grid

    # Initialize stock price, drift, and volatility arrays
    S = np.zeros(shape=N, dtype=np.float64)
    mu = np.zeros(shape=N, dtype=np.float64)
    sigma = np.zeros(shape=N, dtype=np.float64)
    np.random.seed(seed)  # For reproducibility
    W_stock = np.random.standard_normal(size=N)  # Random component for stock price
    W_vol = np.random.standard_normal(size=N)  # Random component for volatility

    # Set initial values
    S[0] = S_0
    mu[0] = mu_0
    sigma[0] = sigma_0

    for i in range(1, N):
        # Stochastic drift: Random walk with slight mean-reversion
        mu[i] = mu[i - 1] + np.random.normal(loc=0, scale=0.005)  # Small changes in drift

        # Stochastic volatility: Heston model (mean-reverting)
        sigma[i] = sigma[i - 1] + kappa * (theta - sigma[i - 1]) * dt + eta * np.sqrt(dt) * W_vol[i]
        sigma[i] = np.maximum(sigma[i], 0.01)  # Ensure positive volatility

        # Stock price follows modified GBM with changing mu and sigma
        S[i] = S[i - 1] * np.exp((mu[i] - 0.5 * sigma[i] ** 2) * dt + sigma[i] * np.sqrt(dt) * W_stock[i])

    return S


def add_noise(
    stock_prices,
    base_vol=0.01,
    vol_spike_prob=0.1,
    spike_factor=3,
    jump_prob=0.02,
    jump_magnitude=0.05,
    seed=42,
) -> np.ndarray:
    N = len(stock_prices)

    np.random.seed(seed)  # For reproducibility
    # Step 1: Gaussian Noise (Micro fluctuations)
    noise = np.random.normal(loc=0, scale=base_vol, size=N) * stock_prices

    # Step 2: GARCH-Like Volatility Clustering (Random High/Low Volatility Phases)
    spikes = np.random.rand(N) < vol_spike_prob  # Boolean array for volatility spikes
    noise[spikes] *= spike_factor  # Increase volatility in some places

    # Step 3: Jump Diffusion (Sudden Large Moves)
    jumps = np.random.rand(N) < jump_prob  # Boolean array for jump occurrences
    jump_size = np.random.uniform(low=-jump_magnitude, high=jump_magnitude, size=N) * stock_prices
    noise += jumps * jump_size  # Apply jumps where they occur

    # Final Noisy Prices
    stock_prices += noise

    return stock_prices


def simulate_stock_returns(S_0, mu_0, sigma_0, D, N):
    stock_returns = np.array(
        object=[simulate_stock_price(S_0=S_0, mu_0=mu_0, sigma_0=sigma_0, N=D) for _ in range(N)],
        dtype=np.float64,
    )

    market_trend = np.mean(a=stock_returns, axis=0)  # Average across stocks
    market_trend = add_noise(stock_prices=market_trend)

    for i in range(stock_returns.shape[0]):
        stock_returns[i] = add_noise(stock_prices=stock_returns[i])

    return stock_returns, market_trend


### End of simulation code ###


def get_starting_parameters():
    # Parameters
    S_0 = 100  # Initial stock price
    mu_0 = 0.05  # Initial expected return (5%)
    sigma_0 = 0.2  # Initial volatility (20%)
    D = 100  # Number of time steps (daily for 1 year)

    # TODO increase N to 1000 for more realistic data
    N = 10

    # Simulate stock market
    stock_returns, market_trend = simulate_stock_returns(S_0=S_0, mu_0=mu_0, sigma_0=sigma_0, D=D, N=N)
    np.random.seed(42)  # For reproducibility
    p = np.random.choice(a=[1, 3, 4, 5, 6, 7, 8, 9, 10])

    return stock_returns, market_trend, p


def most_consistent_stock(stock_returns, market_trend, p):
    dists = np.array([np.linalg.norm(stock - market_trend, ord=p) for stock in stock_returns])
    index = np.argmin(dists)
    p_norm = dists[index]

    return index, p_norm


@pytest.mark.grading_data(name="index", points=1)
def test_0(sandbox: StudentFixture) -> None:
    stock_returns, market_trend, p = get_starting_parameters()

    correct_index, _ = most_consistent_stock(stock_returns, market_trend, p)
    student_index, _ = sandbox.query_function("most_consistent_stock", stock_returns, market_trend, p)

    assert correct_index == student_index, "The index of the most consistent stock is incorrect."


@pytest.mark.grading_data(name="p_norm", points=1)
def test_1(sandbox: StudentFixture) -> None:
    stock_returns, market_trend, p = get_starting_parameters()

    _, correct_p_norm = most_consistent_stock(stock_returns, market_trend, p)
    _, student_p_norm = sandbox.query_function("most_consistent_stock", stock_returns, market_trend, p)

    assert correct_p_norm == student_p_norm, "The p_norm of the most consistent stock is incorrect."
