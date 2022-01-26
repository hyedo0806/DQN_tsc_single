import random
class Memory:
    def __init__(self, size_max, size_min, epsilon_min, epsilon_decay):
        self._samples = []
        self._size_max = size_max
        self._size_min = size_min
        self._epsilon_min = epsilon_min
        self._epsilon_decay = epsilon_decay


    def add_sample(self, sample, epsilon):
        self._samples.append(sample)
        if self._size_max < len(self._samples):
            self._samples.pop(0)
            if epsilon > self._epsilon_min:
                epsilon *= self._epsilon_decay
        return epsilon


    def get_samples(self, n):
        """
        Get n samples randomly from the memory
        """
        if self._size_now() < self._size_min:
            return []

        if n > self._size_now():
            return random.sample(self._samples, self._size_now())  # get all the samples
        else:
            return random.sample(self._samples, n)  # get "batch size" number of samples


    def _size_now(self):
        """
        Check how full the memory is
        """
        return len(self._samples)